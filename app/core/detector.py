"""Local per-frame civic object segmentation and tracking with YOLOE (open-vocabulary YOLO).

Gemini (Pass A/B/C) decides *what is happening* in a clip; this module finds *where each
object is in every frame*: a pixel mask, a persistent track ID and a class for each piece
of garbage, drain, pothole, person and vehicle, plus a waste-type for garbage
(dry/wet/C&D/e-waste/mixed, following India's Solid Waste Management Rules 2016).
"""

import hashlib
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.config import settings

logger = logging.getLogger("civiceye.detector")


@dataclass(frozen=True)
class ObjectClass:
    prompt: str                       # text prompt given to YOLOE
    category: str                     # garbage | bin | drainage | road | person | vehicle | plate
    label: str                        # display label
    waste_type: Optional[str] = None  # set for garbage classes only


OBJECT_CLASSES: List[ObjectClass] = [
    # Garbage, sorted by waste stream
    ObjectClass("plastic bag", "garbage", "plastic bag", "dry_plastic"),
    ObjectClass("plastic bottle", "garbage", "plastic bottle", "dry_plastic"),
    ObjectClass("cardboard box", "garbage", "cardboard", "dry_paper"),
    ObjectClass("paper waste", "garbage", "paper waste", "dry_paper"),
    ObjectClass("food waste", "garbage", "food waste", "wet_organic"),
    ObjectClass("rotting vegetables", "garbage", "vegetable waste", "wet_organic"),
    ObjectClass("construction rubble", "garbage", "construction debris", "construction"),
    ObjectClass("electronic waste", "garbage", "e-waste", "e_waste"),
    ObjectClass("garbage pile", "garbage", "garbage pile", "mixed"),
    ObjectClass("garbage bin", "bin", "garbage bin"),
    # Drainage and road
    ObjectClass("manhole", "drainage", "manhole"),
    ObjectClass("open drain", "drainage", "open drain"),
    ObjectClass("storm drain grate", "drainage", "drain grate"),
    ObjectClass("stagnant water puddle", "drainage", "standing water"),
    ObjectClass("pothole", "road", "pothole"),
    # Actors
    ObjectClass("person", "person", "person"),
    ObjectClass("motorcycle", "vehicle", "two-wheeler"),
    ObjectClass("car", "vehicle", "car"),
    ObjectClass("auto rickshaw", "vehicle", "auto-rickshaw"),
    ObjectClass("truck", "vehicle", "truck"),
    ObjectClass("bus", "vehicle", "bus"),
    ObjectClass("bicycle", "vehicle", "bicycle"),
    ObjectClass("license plate", "plate", "number plate"),
]

WASTE_TYPE_LABELS: Dict[str, str] = {
    "dry_plastic": "Dry - plastic",
    "dry_paper": "Dry - paper/cardboard",
    "wet_organic": "Wet - organic",
    "construction": "C&D debris",
    "e_waste": "E-waste",
    "mixed": "Mixed / unsegregated",
}

CATEGORY_LABELS: Dict[str, str] = {
    "garbage": "Garbage",
    "bin": "Bins",
    "drainage": "Drainage",
    "road": "Road damage",
    "person": "People",
    "vehicle": "Vehicles",
    "plate": "Number plates",
}


@dataclass
class FrameDetection:
    track_id: Optional[int]           # None until the tracker confirms the object
    cls: ObjectClass
    confidence: float
    box: Tuple[int, int, int, int]    # x1, y1, x2, y2 in pixels
    polygon: Optional[np.ndarray]     # (N, 2) int32 mask outline in pixels


def build_detector_model(model_name: str) -> Path:
    """Return a YOLOE model file with OBJECT_CLASSES baked in, building it on first use.

    Building downloads the base weights and a ~250 MB text encoder and takes a few minutes
    the first time; afterwards the baked model loads in well under a second with no
    text encoder. Run scripts/prepare_detector.py once to do this ahead of time.
    """
    names = [c.prompt for c in OBJECT_CLASSES]
    key = hashlib.sha1("|".join([model_name, *names]).encode()).hexdigest()[:10]
    models_dir = settings.MODELS_DIR
    baked = models_dir / f"civiceye-{Path(model_name).stem}-{key}.pt"
    if baked.is_file():
        return baked

    from ultralytics import YOLOE

    logger.info("Building detector model %s (first run downloads weights and text encoder)...", baked.name)
    models_dir.mkdir(parents=True, exist_ok=True)
    # Ultralytics downloads the base weights and text encoder into the working directory
    cwd = os.getcwd()
    os.chdir(models_dir)
    try:
        model = YOLOE(model_name)
        model.set_classes(names, model.get_text_pe(names))
        model.save(baked.name)
    finally:
        os.chdir(cwd)
    return baked


class CivicObjectDetector:
    """Wraps a YOLOE segmentation model prompted with OBJECT_CLASSES and a ByteTrack tracker."""

    def __init__(self, model_name: Optional[str] = None, conf: Optional[float] = None, imgsz: Optional[int] = None):
        self.model_name = model_name or settings.DETECTOR_MODEL
        self.conf = conf if conf is not None else settings.DETECTOR_CONF
        self.imgsz = imgsz or settings.DETECTOR_IMGSZ
        self._model = None

    def _load(self):
        from ultralytics import YOLOE  # heavy import, only when detection actually runs

        baked = build_detector_model(self.model_name)
        return YOLOE(str(baked))

    def start_video(self) -> None:
        """Start a fresh tracking session (track IDs restart for each video)."""
        self._model = self._load()

    def track(self, frame: np.ndarray) -> List[FrameDetection]:
        if self._model is None:
            self.start_video()
        result = self._model.track(
            frame, persist=True, conf=self.conf, imgsz=self.imgsz,
            tracker="bytetrack.yaml", verbose=False,
        )[0]
        return parse_result(result)


def parse_result(result) -> List[FrameDetection]:
    """Convert an ultralytics Result into FrameDetections."""
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return []
    xyxy = boxes.xyxy.cpu().numpy().astype(int)
    cls_idx = boxes.cls.cpu().numpy().astype(int)
    confs = boxes.conf.cpu().numpy()
    ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [None] * len(xyxy)
    polygons = result.masks.xy if result.masks is not None else [None] * len(xyxy)

    detections = []
    for box, c, conf, tid, poly in zip(xyxy, cls_idx, confs, ids, polygons):
        if not 0 <= c < len(OBJECT_CLASSES):
            continue
        polygon = poly.astype(np.int32) if poly is not None and len(poly) >= 3 else None
        detections.append(FrameDetection(
            track_id=int(tid) if tid is not None else None,
            cls=OBJECT_CLASSES[c],
            confidence=float(conf),
            box=tuple(int(v) for v in box),
            polygon=polygon,
        ))
    return detections


def detection_area(det: FrameDetection) -> float:
    """Mask area in pixels (box area if no mask)."""
    if det.polygon is not None:
        import cv2
        return float(cv2.contourArea(det.polygon))
    x1, y1, x2, y2 = det.box
    return float(max(0, x2 - x1) * max(0, y2 - y1))


class VideoObjectSummary:
    """Aggregates per-frame detections into per-object tracks and video-level statistics."""

    MIN_FRAMES = 2  # tracks seen in fewer analysed frames are treated as flicker

    def __init__(self, frame_w: int, frame_h: int):
        self.frame_area = float(max(1, frame_w * frame_h))
        self.frames_analyzed = 0
        self._tracks: Dict[int, dict] = {}
        self._timeline: Dict[int, Dict[str, int]] = {}
        self.max_garbage_coverage = 0.0

    def add(self, sec: float, detections: List[FrameDetection]) -> None:
        self.frames_analyzed += 1
        garbage_area = 0.0
        counts: Dict[str, int] = defaultdict(int)
        for det in detections:
            counts[det.cls.category] += 1
            area = detection_area(det)
            if det.cls.category == "garbage":
                garbage_area += area
            if det.track_id is None:
                continue
            t = self._tracks.setdefault(det.track_id, {
                "votes": defaultdict(float), "first_sec": sec, "last_sec": sec,
                "frames": 0, "max_conf": 0.0, "max_area": 0.0,
            })
            t["votes"][det.cls.prompt] += det.confidence
            t["last_sec"] = sec
            t["frames"] += 1
            t["max_conf"] = max(t["max_conf"], det.confidence)
            t["max_area"] = max(t["max_area"], area)

        self.max_garbage_coverage = max(self.max_garbage_coverage, garbage_area / self.frame_area)
        bucket = self._timeline.setdefault(int(sec), defaultdict(int))
        for cat, n in counts.items():
            bucket[cat] = max(bucket[cat], n)

    def objects(self) -> List[dict]:
        by_prompt = {c.prompt: c for c in OBJECT_CLASSES}
        out = []
        for tid, t in sorted(self._tracks.items()):
            if t["frames"] < self.MIN_FRAMES:
                continue
            # A track's class can flicker (e.g. "plastic bag" vs "garbage pile"); use the
            # confidence-weighted majority over all frames.
            cls = by_prompt[max(t["votes"], key=t["votes"].get)]
            out.append({
                "track_id": tid,
                "label": cls.label,
                "category": cls.category,
                "waste_type": cls.waste_type,
                "first_sec": round(t["first_sec"], 2),
                "last_sec": round(t["last_sec"], 2),
                "frames_seen": t["frames"],
                "max_confidence": round(t["max_conf"], 3),
                "max_area_fraction": round(t["max_area"] / self.frame_area, 4),
            })
        return out

    def to_dict(self, model_name: str) -> dict:
        objects = self.objects()
        counts: Dict[str, int] = defaultdict(int)
        waste: Dict[str, int] = defaultdict(int)
        for o in objects:
            counts[o["category"]] += 1
            if o["waste_type"]:
                waste[o["waste_type"]] += 1
        return {
            "detector": model_name,
            "frames_analyzed": self.frames_analyzed,
            "objects": objects,
            "counts_by_category": dict(counts),
            "waste_breakdown": dict(waste),
            "max_garbage_coverage": round(self.max_garbage_coverage, 4),
            "timeline": [{"sec": s, **dict(c)} for s, c in sorted(self._timeline.items())],
        }
