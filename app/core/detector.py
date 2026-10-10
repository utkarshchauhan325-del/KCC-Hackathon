"""Local per-frame civic object segmentation and tracking with YOLOE (open-vocabulary YOLO).

Gemini (Pass A/B/C) decides *what is happening* in a clip; this module finds *where each
object is in every frame*. Garbage is learned per video from boxes Gemini draws on a few
frames (visual prompts), because text prompts alone miss most real-world garbage.
Every garbage region, drain, pothole, person and vehicle gets a pixel mask, a persistent
track ID and a class; garbage also gets a waste stream (dry/wet/C&D/e-waste/mixed,
following India's Solid Waste Management Rules 2016).
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
    # Garbage is not text-prompted: it is learned per video from Gemini examples
    # (VISUAL_GARBAGE_CLASSES), since text prompts mislabel walls and miss real heaps.
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
    contours: List[np.ndarray]        # mask outlines in pixels, one (N, 2) int32 array per separate piece


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


# Garbage classes learned from Gemini-located examples (visual prompts), one per waste stream.
# Text prompts alone barely register dense real-world garbage; example boxes do.
VISUAL_GARBAGE_CLASSES: Dict[str, ObjectClass] = {
    "dry_plastic": ObjectClass("vp:dry_plastic", "garbage", "plastic waste", "dry_plastic"),
    "dry_paper": ObjectClass("vp:dry_paper", "garbage", "paper waste", "dry_paper"),
    "wet_organic": ObjectClass("vp:wet_organic", "garbage", "organic waste", "wet_organic"),
    "construction": ObjectClass("vp:construction", "garbage", "construction debris", "construction"),
    "e_waste": ObjectClass("vp:e_waste", "garbage", "e-waste", "e_waste"),
    "mixed": ObjectClass("vp:mixed", "garbage", "mixed garbage", "mixed"),
}

TRACKER_CONFIG = Path(__file__).with_name("civiceye_botsort.yaml")


@dataclass
class GarbageExemplar:
    """A frame with Gemini-located garbage boxes, used to build visual prompts."""
    image: np.ndarray                          # BGR frame
    boxes: List[Tuple[int, int, int, int]]     # x1, y1, x2, y2 in pixels
    waste_types: List[str]                     # one per box


class CivicObjectDetector:
    """YOLOE segmentation over text-prompted classes plus Gemini-exemplar garbage classes,
    tracked with BoT-SORT (camera-motion compensated, for handheld and moving footage)."""

    def __init__(self, model_name: Optional[str] = None, conf: Optional[float] = None, imgsz: Optional[int] = None):
        self.model_name = model_name or settings.DETECTOR_MODEL
        self.conf = conf if conf is not None else settings.DETECTOR_CONF
        self.vp_conf = settings.DETECTOR_VP_CONF
        self.imgsz = imgsz or settings.DETECTOR_IMGSZ
        self.exemplars: List[GarbageExemplar] = []
        self.classes: List[ObjectClass] = list(OBJECT_CLASSES)
        self._model = None
        self._tracker = None

    def set_exemplars(self, exemplars: List[GarbageExemplar]) -> None:
        """Garbage examples for the next video; applied by start_video()."""
        self.exemplars = [e for e in exemplars if e.boxes]

    def start_video(self) -> None:
        """Load the model with this video's classes and start a fresh tracker (IDs restart)."""
        from ultralytics import YOLOE
        from ultralytics.trackers.bot_sort import BOTSORT
        from ultralytics.utils import YAML, IterableSimpleNamespace

        model = YOLOE(str(build_detector_model(self.model_name)))
        self.classes = list(OBJECT_CLASSES)
        if self.exemplars:
            vp_classes, vpe = _visual_prompt_embeddings(model, self.exemplars, self.imgsz)
            text_pe = model.model.pe.to(vpe.device, vpe.dtype)
            self.classes = list(OBJECT_CLASSES) + vp_classes
            model.set_classes([c.prompt for c in self.classes], torch_cat([text_pe, vpe], dim=1))
        self._model = model
        self._tracker = BOTSORT(args=IterableSimpleNamespace(**YAML.load(TRACKER_CONFIG)))

    def track(self, frame: np.ndarray) -> List[FrameDetection]:
        if self._model is None:
            self.start_video()
        result = self._model.predict(frame, conf=min(self.conf, self.vp_conf), imgsz=self.imgsz, verbose=False)[0]
        # Exemplar classes score lower than text classes, so each gets its own threshold
        thresholds = np.array([self.vp_conf if c.prompt.startswith("vp:") else self.conf for c in self.classes])
        if len(result.boxes):
            keep = result.boxes.conf.cpu().numpy() >= thresholds[result.boxes.cls.cpu().numpy().astype(int)]
            result = result[keep]
        # Only countable things are tracked; garbage is measured as area (see VideoObjectSummary)
        cls_idx = result.boxes.cls.cpu().numpy().astype(int) if len(result.boxes) else np.empty(0, dtype=int)
        countable = np.flatnonzero([self.classes[c].category != "garbage" for c in cls_idx]).astype(int)
        track_by_det: Dict[int, int] = {}
        if len(countable):
            tracks = self._tracker.update(result[countable].boxes.cpu().numpy(), frame)
            # Unconfirmed detections are still drawn, without an ID
            track_by_det = {int(countable[int(t[7])]): int(t[4]) for t in tracks}
        return parse_result(result, self.classes, track_by_det)


CivicDetector = CivicObjectDetector


def torch_cat(tensors, dim: int):
    import torch
    return torch.cat(tensors, dim=dim)


def _visual_prompt_embeddings(model, exemplars: List[GarbageExemplar], imgsz: int):
    """Average YOLOE visual-prompt embeddings per waste type across all exemplar frames."""
    import torch
    import torch.nn.functional as F
    from ultralytics.models.yolo.yoloe import YOLOEVPSegPredictor

    predictor = YOLOEVPSegPredictor(overrides=dict(task="segment", mode="predict", save=False, batch=1, verbose=False, imgsz=imgsz))
    per_type: Dict[str, list] = defaultdict(list)
    for ex in exemplars:
        types_here = sorted(set(ex.waste_types))
        local = np.array([types_here.index(t) for t in ex.waste_types])
        predictor.set_prompts({"bboxes": np.array(ex.boxes, dtype=np.float32), "cls": local})
        predictor.setup_model(model=model.model, verbose=False)
        predictor.model.names = {i: f"object{i}" for i in range(len(types_here))}
        vpe = predictor.get_vpe(ex.image)  # (1, len(types_here), D)
        for j, t in enumerate(types_here):
            per_type[t].append(vpe[0, j])
    order = [t for t in VISUAL_GARBAGE_CLASSES if t in per_type]
    pe = torch.stack([F.normalize(torch.stack(per_type[t]).mean(0), dim=-1) for t in order]).unsqueeze(0)
    return [VISUAL_GARBAGE_CLASSES[t] for t in order], pe


def parse_result(result, classes: List[ObjectClass], track_by_det: Optional[Dict[int, int]] = None) -> List[FrameDetection]:
    """Convert an ultralytics Result into FrameDetections; track_by_det maps detection index -> track ID."""
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return []
    track_by_det = track_by_det or {}
    xyxy = boxes.xyxy.cpu().numpy().astype(int)
    cls_idx = boxes.cls.cpu().numpy().astype(int)
    confs = boxes.conf.cpu().numpy()
    all_contours = mask_contours(result) if getattr(result, "masks", None) is not None else [[] for _ in xyxy]

    detections = []
    for i, (box, c, conf, contours) in enumerate(zip(xyxy, cls_idx, confs, all_contours)):
        if not 0 <= c < len(classes):
            continue
        detections.append(FrameDetection(
            track_id=track_by_det.get(i),
            cls=classes[c],
            confidence=float(conf),
            box=tuple(int(v) for v in box),
            contours=contours,
        ))
    return detections


def mask_contours(result, min_area_px: float = 30.0) -> List[List[np.ndarray]]:
    """Outline every separate piece of each mask, in original-image pixels.

    Ultralytics' Masks.xy joins a mask's pieces into one polygon with connecting
    segments, which draws long straight lines across the frame; keep pieces separate.
    """
    import cv2
    try:
        from ultralytics.utils.ops import scale_coords
    except ImportError:
        def scale_coords(img1_shape, coords, img0_shape):
            h1, w1 = img1_shape[:2]
            h0, w0 = img0_shape[:2]
            gain = min(h1 / h0, w1 / w0) if h0 and w0 else 1.0
            pad_x = (w1 - w0 * gain) / 2.0
            pad_y = (h1 - h0 * gain) / 2.0
            pts = coords.copy()
            pts[:, 0] = (pts[:, 0] - pad_x) / (gain or 1.0)
            pts[:, 1] = (pts[:, 1] - pad_y) / (gain or 1.0)
            return pts

    data = result.masks.data.cpu().numpy().astype(np.uint8)
    orig_h, orig_w = result.orig_shape[:2]
    out = []
    for m in data:
        pieces = []
        for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            if len(c) < 3:
                continue
            pts = scale_coords(m.shape, c.reshape(-1, 2).astype(np.float32), (orig_h, orig_w))
            pts = np.round(pts).astype(np.int32)
            if cv2.contourArea(pts) >= min_area_px:
                pieces.append(pts)
        out.append(pieces)
    return out


def detection_area(det: FrameDetection) -> float:
    """Mask area in pixels (box area if no mask)."""
    if det.contours:
        import cv2
        return float(sum(cv2.contourArea(c) for c in det.contours))
    x1, y1, x2, y2 = det.box
    return float(max(0, x2 - x1) * max(0, y2 - y1))


class VideoObjectSummary:
    """Aggregates per-frame detections into video-level statistics.

    Countable things (people, vehicles, drains, potholes, plates) are tracked objects.
    Garbage is measured as area instead: heaps have no stable boundary between frames,
    so tracking them as objects only produces churn. Coverage is the union of garbage
    masks as a fraction of the frame, measured on a downscaled raster.
    """

    RASTER = 160  # longer side of the raster used to measure mask union area

    def __init__(self, frame_w: int, frame_h: int, min_frames: int = 2):
        self.min_frames = min_frames  # tracks seen in fewer analysed frames are treated as flicker
        self.frame_area = float(max(1, frame_w * frame_h))
        self._scale = self.RASTER / max(frame_w, frame_h, 1)
        self._raster_shape = (max(1, round(frame_h * self._scale)), max(1, round(frame_w * self._scale)))
        self.frames_analyzed = 0
        self._tracks: Dict[int, dict] = {}
        self._timeline: Dict[int, Dict[str, float]] = {}
        self._coverage: List[float] = []
        self._waste_area: Dict[str, float] = defaultdict(float)

    def _garbage_union(self, detections: List[FrameDetection]) -> Tuple[float, Dict[str, float]]:
        """Fraction of the frame covered by garbage, and covered fraction per waste stream."""
        import cv2

        union = np.zeros(self._raster_shape, dtype=np.uint8)
        per_type: Dict[str, np.ndarray] = {}
        for det in detections:
            if det.cls.category != "garbage":
                continue
            layer = per_type.setdefault(det.cls.waste_type or "mixed", np.zeros(self._raster_shape, dtype=np.uint8))
            if det.contours:
                cv2.fillPoly(layer, [np.round(c * self._scale).astype(np.int32) for c in det.contours], 1)
            else:
                x1, y1, x2, y2 = (round(v * self._scale) for v in det.box)
                layer[y1:y2, x1:x2] = 1
        for layer in per_type.values():
            union |= layer
        total = float(union.size)
        return float(union.sum()) / total, {k: float(v.sum()) / total for k, v in per_type.items()}

    def add(self, sec: float, detections: List[FrameDetection]) -> None:
        self.frames_analyzed += 1
        counts: Dict[str, int] = defaultdict(int)
        for det in detections:
            if det.cls.category == "garbage":
                continue
            counts[det.cls.category] += 1
            if det.track_id is None:
                continue
            t = self._tracks.setdefault(det.track_id, {
                "votes": defaultdict(float), "first_sec": sec, "last_sec": sec,
                "frames": 0, "max_conf": 0.0, "max_area": 0.0,
            })
            t["votes"][det.cls] += det.confidence
            t["last_sec"] = sec
            t["frames"] += 1
            t["max_conf"] = max(t["max_conf"], det.confidence)
            t["max_area"] = max(t["max_area"], detection_area(det))

        coverage, per_type = self._garbage_union(detections)
        self._coverage.append(coverage)
        for k, v in per_type.items():
            self._waste_area[k] += v

        bucket = self._timeline.setdefault(int(sec), defaultdict(float))
        for cat, n in counts.items():
            bucket[cat] = max(bucket[cat], n)
        bucket["garbage_coverage"] = max(bucket["garbage_coverage"], round(coverage, 4))

    def objects(self) -> List[dict]:
        out = []
        for tid, t in sorted(self._tracks.items()):
            if t["frames"] < self.min_frames:
                continue
            # A track's class can flicker between frames; use the confidence-weighted majority.
            cls = max(t["votes"], key=t["votes"].get)
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

    def garbage_coverage(self) -> float:
        """Typical heavy coverage: 90th percentile over analysed frames, robust to one bad frame."""
        return float(np.percentile(self._coverage, 90)) if self._coverage else 0.0

    def to_dict(self, model_name: str, exemplar_frames: int = 0, garbage_measured: bool = True) -> dict:
        """garbage_measured=False (no Gemini examples) reports garbage fields as None, not 0."""
        objects = self.objects()
        counts: Dict[str, int] = defaultdict(int)
        for o in objects:
            counts[o["category"]] += 1
        waste_total = sum(self._waste_area.values())
        frames_with_garbage = sum(1 for c in self._coverage if c > 0.005)
        return {
            "detector": model_name,
            "garbage_exemplar_frames": exemplar_frames,
            "min_frames": self.min_frames,
            "frames_analyzed": self.frames_analyzed,
            "objects": objects,
            # Track counts overstate people/vehicles when the camera pans or objects overlap
            # (one person can get several IDs); the most seen in a single frame is robust to that.
            "counts_by_category": dict(counts),
            "peak_in_frame": {
                cat: int(max(row.get(cat, 0) for row in self._timeline.values()))
                for cat in {k for row in self._timeline.values() for k in row if k != "garbage_coverage"}
            },
            "garbage_measured": garbage_measured,
            # Share of all garbage area by waste stream (fractions summing to 1)
            "waste_breakdown": {k: round(v / waste_total, 3) for k, v in self._waste_area.items()} if waste_total else {},
            "garbage_coverage": round(self.garbage_coverage(), 4) if garbage_measured else None,
            "max_garbage_coverage": round(max(self._coverage, default=0.0), 4) if garbage_measured else None,
            "garbage_frame_fraction": (
                round(frames_with_garbage / self.frames_analyzed, 3) if self.frames_analyzed and garbage_measured else None
            ),
            "timeline": [{"sec": s, **dict(c)} for s, c in sorted(self._timeline.items())],
        }
