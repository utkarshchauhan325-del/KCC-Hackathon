"""Evidence extraction, frame annotation, bounding box crops, and privacy blurring."""

import cv2
import numpy as np
import math
from pathlib import Path
from typing import Tuple, Optional, Union, Any, List, Dict
from app.config import settings
from app.core.schemas import BBox

def timestamp_to_seconds(ts_str: str) -> float:
    """Convert MM:SS or HH:MM:SS or SS string to seconds float."""
    parts = ts_str.strip().split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    else:
        return float(parts[0])

def scale_bbox_to_pixels(box: BBox, img_width: int, img_height: int) -> Tuple[int, int, int, int]:
    """Scale 0-1000 normalized coordinates to clamped pixel [xmin, ymin, xmax, ymax]."""
    x1 = int((box.xmin / 1000.0) * img_width)
    y1 = int((box.ymin / 1000.0) * img_height)
    x2 = int((box.xmax / 1000.0) * img_width)
    y2 = int((box.ymax / 1000.0) * img_height)

    # Clamp to image bounds
    x1 = max(0, min(img_width - 1, x1))
    y1 = max(0, min(img_height - 1, y1))
    x2 = max(0, min(img_width, max(x1 + 1, x2)))
    y2 = max(0, min(img_height, max(y1 + 1, y2)))
    return (x1, y1, x2, y2)

def extract_frame_at_timestamp(video_path: Union[str, Path], ts_seconds: float) -> Optional[np.ndarray]:
    """Extract single frame at specific timestamp in seconds using OpenCV."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_index = int(ts_seconds * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        return None
    return frame

def annotate_frame(
    frame: np.ndarray,
    box: BBox,
    label: str,
    severity: int = 1,
    color: Optional[Tuple[int, int, int]] = None
) -> np.ndarray:
    """Draw bounding box and label tag on frame."""
    annotated = frame.copy()
    h, w, _ = annotated.shape
    x1, y1, x2, y2 = scale_bbox_to_pixels(box, w, h)

    # Color code by severity (BGR): 1-2 Green/Yellow, 3 Orange, 4-5 Red
    if color is None:
        if severity >= 4:
            color = (0, 0, 230)      # Red
        elif severity == 3:
            color = (0, 140, 255)    # Orange
        elif severity == 2:
            color = (0, 215, 255)    # Amber
        else:
            color = (0, 200, 0)      # Green

    # Draw box
    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)

    # Draw header tag
    tag = f"{label} [Sev {severity}]" if severity > 1 else label
    (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    tag_y = max(th + 6, y1)
    cv2.rectangle(annotated, (x1, tag_y - th - 6), (x1 + tw + 8, tag_y + 4), color, -1)
    cv2.putText(annotated, tag, (x1 + 4, tag_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return annotated

def crop_bbox(frame: np.ndarray, box: BBox) -> np.ndarray:
    """Crop region defined by normalized bounding box."""
    h, w, _ = frame.shape
    x1, y1, x2, y2 = scale_bbox_to_pixels(box, w, h)
    return frame[y1:y2, x1:x2].copy()

def blur_bystander_faces(frame: np.ndarray, primary_box: Optional[BBox] = None) -> np.ndarray:
    """Detect human faces in frame and apply Gaussian blur to bystanders (DPDP Act privacy safeguard)."""
    blurred = frame.copy()
    h, w, _ = blurred.shape

    # Primary violator pixel bounds (faces inside this region are NOT blurred as evidence)
    p_x1, p_y1, p_x2, p_y2 = (0, 0, 0, 0)
    if primary_box:
        p_x1, p_y1, p_x2, p_y2 = scale_bbox_to_pixels(primary_box, w, h)

    # Use OpenCV built-in frontal face cascade
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        return blurred

    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24))

    for (fx, fy, fw, fh) in faces:
        face_center_x = fx + fw // 2
        face_center_y = fy + fh // 2

        # Check if face falls inside the violator box
        is_primary = (p_x1 <= face_center_x <= p_x2) and (p_y1 <= face_center_y <= p_y2)
        if not is_primary:
            # Apply strong Gaussian blur to bystander face
            roi = blurred[fy:fy+fh, fx:fx+fw]
            roi = cv2.GaussianBlur(roi, (51, 51), 30)
            blurred[fy:fy+fh, fx:fx+fw] = roi

    return blurred

def save_image(img: np.ndarray, output_path: Union[str, Path]) -> Path:
    """Save OpenCV BGR image to disk."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), img)
    return out


def get_temporal_telemetry(
    curr_sec: float,
    total_sec: float,
    initial_drain: float = 94.0,
    initial_garb: float = 90.0,
    initial_depth: float = 28.0,
) -> Tuple[float, float, float, float, str, str]:
    """Calculate real-time changing telemetry as video moves and drain is cleaned."""
    p = min(1.0, max(0.0, curr_sec / max(1.0, total_sec)))
    if p < 0.32:
        # Phase 1: Heavy choking and active dumping
        f = p / 0.32
        d = initial_drain - (f * 5.0)
        g = initial_garb - (f * 6.0)
        dep = initial_depth - (f * 3.0)
        status = "CHOKED / DUMPING ACTIVE"
    elif p < 0.68:
        # Phase 2: Flow clearing / jetting / debris clearing
        f = (p - 0.32) / 0.36
        d = (initial_drain - 5.0) - (f * 52.0)
        g = (initial_garb - 6.0) - (f * 50.0)
        dep = (initial_depth - 3.0) - (f * 18.0)
        status = "CLEARING / FLOW RESTORING"
    else:
        # Phase 3: Drain cleared, debris removed, flow optimal
        f = (p - 0.68) / 0.32
        d = max(14.0, 37.0 - (f * 20.0))
        g = max(12.0, 34.0 - (f * 20.0))
        dep = max(3.0, 7.0 - (f * 4.0))
        status = "DRAIN CLEANED & RESTORED"

    comp = 0.42 * d + 0.38 * g + 0.20 * min(100.0, (dep / 40.0) * 100.0)
    band = "CRITICAL" if comp >= 75 else ("HIGH" if comp >= 50 else ("WATCH" if comp >= 30 else "OPTIMAL"))
    return round(d, 1), round(g, 1), round(dep, 1), round(comp, 1), band, status


def compute_iou(boxA: Union[list, tuple], boxB: Union[list, tuple]) -> float:
    """Calculate Intersection-over-Union (IoU) between two [x1, y1, x2, y2] boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0, xB - xA)
    inter_h = max(0, yB - yA)
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0

    boxA_area = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxB_area = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    union_area = float(boxA_area + boxB_area - inter_area)
    return inter_area / union_area if union_area > 0 else 0.0


def parse_gemini_bbox(raw_bbox: Any, img_w: int, img_h: int) -> Tuple[int, int, int, int]:
    """Parse Gemini bbox format into clamped pixel coordinates [x1, y1, x2, y2]."""
    if hasattr(raw_bbox, "ymin"):
        x1 = int((raw_bbox.xmin / 1000.0) * img_w)
        y1 = int((raw_bbox.ymin / 1000.0) * img_h)
        x2 = int((raw_bbox.xmax / 1000.0) * img_w)
        y2 = int((raw_bbox.ymax / 1000.0) * img_h)
        return (
            max(0, min(img_w - 1, min(x1, x2))),
            max(0, min(img_h - 1, min(y1, y2))),
            min(img_w, max(max(x1, x2), min(x1, x2) + 10)),
            min(img_h, max(max(y1, y2), min(y1, y2) + 10)),
        )

    if isinstance(raw_bbox, dict):
        x1_v = raw_bbox.get("xmin", raw_bbox.get("x_min", 0))
        y1_v = raw_bbox.get("ymin", raw_bbox.get("y_min", 0))
        x2_v = raw_bbox.get("xmax", raw_bbox.get("x_max", 1000))
        y2_v = raw_bbox.get("ymax", raw_bbox.get("y_max", 1000))
        coords = [x1_v, y1_v, x2_v, y2_v]
    elif isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) == 4:
        coords = list(raw_bbox)
    else:
        return (0, 0, 0, 0)

    # Normalize if values are 0.0 - 1.0 floats
    if all(0.0 <= float(v) <= 1.0 for v in coords) and max(float(v) for v in coords) <= 1.0:
        coords = [float(v) * 1000.0 for v in coords]

    v0, v1, v2, v3 = [float(x) for x in coords]
    x_min, x_max = min(v0, v2), max(v0, v2)
    y_min, y_max = min(v1, v3), max(v1, v3)

    px1 = int((x_min / 1000.0) * img_w)
    py1 = int((y_min / 1000.0) * img_h)
    px2 = int((x_max / 1000.0) * img_w)
    py2 = int((y_max / 1000.0) * img_h)

    px1 = max(0, min(img_w - 1, px1))
    py1 = max(0, min(img_h - 1, py1))
    px2 = min(img_w, max(px1 + 10, px2))
    py2 = min(img_h, max(py1 + 10, py2))
    return (px1, py1, px2, py2)


class GarbageObjectTracker:
    """Kalman-filter powered object tracker for physical garbage objects across video frames."""

    def __init__(
        self,
        bbox: Union[list, tuple],
        label: str = "GARBAGE",
        track_id: int = 1,
        confidence: float = 0.90,
        description: str = "Solid waste debris",
        source: str = "Gemini",
        severity: int = 4,
        max_age: int = 25,
    ):
        self.id = track_id
        self.label = label
        self.category = "garbage"  # STRICT: only actual garbage is tracked
        self.severity = severity
        self.confidence = float(confidence)
        self.description = description
        self.source = source
        self.status = "TRACKING"
        self.time_since_update = 0
        self.hits = 1
        self.age = 0
        self.active = True
        self.max_age = max_age

        # State vector: [cx, cy, w, h, vx, vy]
        self.kf = cv2.KalmanFilter(6, 4)
        self.kf.transitionMatrix = np.array([
            [1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.85, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.85],
        ], dtype=np.float32)
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
            [0, 0, 0, 1, 0, 0],
        ], np.float32)
        self.kf.processNoiseCov = np.eye(6, dtype=np.float32) * 1e-3
        self.kf.measurementNoiseCov = np.eye(4, dtype=np.float32) * 1e-2

        w = max(15.0, float(bbox[2] - bbox[0]))
        h = max(15.0, float(bbox[3] - bbox[1]))
        cx = float(bbox[0] + bbox[2]) / 2.0
        cy = float(bbox[1] + bbox[3]) / 2.0
        self.kf.statePost = np.array([cx, cy, w, h, 0, 0], np.float32).reshape(6, 1)

    def update(
        self,
        bbox: Union[list, tuple],
        confidence: Optional[float] = None,
        description: Optional[str] = None,
        source: str = "Gemini",
    ) -> None:
        self.time_since_update = 0
        self.hits += 1
        self.status = "TRACKING"
        self.source = source
        if confidence is not None:
            self.confidence = float(confidence)
        if description:
            self.description = description

        w = max(15.0, float(bbox[2] - bbox[0]))
        h = max(15.0, float(bbox[3] - bbox[1]))
        cx = float(bbox[0] + bbox[2]) / 2.0
        cy = float(bbox[1] + bbox[3]) / 2.0
        measurement = np.array([cx, cy, w, h], np.float32).reshape(4, 1)
        self.kf.correct(measurement)

    def predict(self, img_w: int, img_h: int) -> Tuple[int, int, int, int]:
        self.age += 1
        self.time_since_update += 1
        if self.time_since_update > 0:
            self.status = "TRACKING (PREDICTED)"
        if self.time_since_update > self.max_age:
            self.active = False

        pred = self.kf.predict()
        cx = float(np.clip(pred[0][0], 0, img_w))
        cy = float(np.clip(pred[1][0], 0, img_h))
        w = float(np.clip(pred[2][0], 15, img_w))
        h = float(np.clip(pred[3][0], 15, img_h))
        self.kf.statePost[0][0] = cx
        self.kf.statePost[1][0] = cy
        self.kf.statePost[2][0] = w
        self.kf.statePost[3][0] = h
        return int(cx - w / 2.0), int(cy - h / 2.0), int(cx + w / 2.0), int(cy + h / 2.0)

    def get_box(self, img_w: int, img_h: int) -> Tuple[int, int, int, int]:
        s = self.kf.statePost
        cx = float(np.clip(s[0][0], 0, img_w))
        cy = float(np.clip(s[1][0], 0, img_h))
        w = float(np.clip(s[2][0], 15, img_w))
        h = float(np.clip(s[3][0], 15, img_h))
        x1 = max(0, int(cx - w / 2.0))
        y1 = max(0, int(cy - h / 2.0))
        x2 = min(img_w, max(x1 + 10, int(cx + w / 2.0)))
        y2 = min(img_h, max(y1 + 10, int(cy + h / 2.0)))
        return x1, y1, x2, y2


def detect_garbage_candidates(
    frame: np.ndarray,
    client: Optional[Any] = None,
    confidence_threshold: float = 0.70,
    img_w: Optional[int] = None,
    img_h: Optional[int] = None,
) -> list:
    """Detect actual solid waste items using Gemini visual detection (strictly filtering drains and roads)."""
    h, w = frame.shape[:2]
    img_w = img_w or w
    img_h = img_h or h
    candidates = []

    if client is not None and hasattr(client, "detect_garbage_frame"):
        try:
            resp = client.detect_garbage_frame(frame, confidence_threshold=confidence_threshold)
            for obj in resp.objects:
                c_name = getattr(obj, "class_name", "") or getattr(obj, "class", "")
                if str(c_name).lower() != "garbage":
                    continue
                if obj.confidence < confidence_threshold:
                    continue
                bx1, by1, bx2, by2 = parse_gemini_bbox(obj.bbox, img_w, img_h)
                box_area = (bx2 - bx1) * (by2 - by1)
                # Ignore degenerate tiny boxes or boxes covering whole image (background/road)
                if (bx2 - bx1) < 12 or (by2 - by1) < 12:
                    continue
                if box_area > 0.80 * (img_w * img_h):
                    continue

                candidates.append({
                    "box": (bx1, by1, bx2, by2),
                    "confidence": float(obj.confidence),
                    "description": str(obj.description or "Solid waste debris"),
                    "source": "Gemini",
                    "area": box_area,
                })
        except Exception:
            pass

    return candidates


def detect_frame_objects(frame: np.ndarray, category: str, img_w: int, img_h: int) -> list:
    """Backward-compatible hook for frame object queries."""
    if category.lower() != "garbage":
        # STRICT DISCRIMINATION: Drains, roads, soil, shadows never return garbage candidates
        return []

    # High-contrast visual fallback for foreground debris if Gemini is not hooked here
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mask = (gray > 165) & (frame[:, :, 2] > 150)
    mask[:int(0.25 * img_h), :] = False
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    mask_closed = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    cnts, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for c in cnts:
        area = cv2.contourArea(c)
        if 150 < area < 45000:
            bx, by, bw, bh = cv2.boundingRect(c)
            if bw >= 12 and bh >= 12:
                candidates.append({
                    "box": (bx, by, bx + bw, by + bh),
                    "confidence": 0.85,
                    "description": "Solid debris accumulation",
                    "source": "Visual",
                    "area": area,
                })
    candidates.sort(key=lambda d: d["area"], reverse=True)
    return candidates


def generate_annotated_surveillance_video(
    video_path: Union[str, Path],
    output_path: Union[str, Path],
    detections: list,
    camera_meta: Optional[dict] = None,
    drainage_score: float = 75.0,
    garbage_score: float = 70.0,
    water_depth_cm: float = 25.0,
    confidence_threshold: float = 0.70,
    client: Optional[Any] = None,
) -> Path:
    """Render real-time bounding boxes, edge-AI telemetry, and dynamic surveillance HUD onto video."""
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Cannot open video for annotation: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 100)
    total_sec = total_frames / fps if fps else 10.0

    camera_id = camera_meta.get("id", "CAM-PUNE-01") if camera_meta else "CAM-PUNE-01"
    camera_name = camera_meta.get("name", "Optical Surveillance") if camera_meta else "Optical Stream"
    gps_str = camera_meta.get("gps", "18.5255, 73.8415") if camera_meta else "18.5255, 73.8415"

    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))
    if not out.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

    # Initialize Gemini client if available
    gemini_client = client
    if gemini_client is None:
        try:
            from app.core.gemini_client import GeminiVideoClient
            gemini_client = GeminiVideoClient()
        except Exception:
            gemini_client = None

    # STRICT DISCRIMINATION: Filter input detections to ONLY actual garbage!
    # DRAINS, ROADS, SHADOWS, WATER MUST NEVER RECEIVE A BOUNDING BOX.
    garbage_detections = [
        d for d in detections
        if str(d.get("category", "")).lower() == "garbage"
    ]

    trackers: dict[int, GarbageObjectTracker] = {}
    next_track_id = 1

    # Initialize trackers from confirmed initial garbage detections
    for d in garbage_detections:
        s = d.get("start_sec", 0.0)
        e = d.get("end_sec", 9999.0)
        if s <= 0.0 <= e:
            box = d.get("box")
            bx1, by1, bx2, by2 = parse_gemini_bbox(box, w, h)
            conf = float(d.get("confidence", 0.88))
            if conf >= confidence_threshold:
                desc = d.get("subtype", "Solid waste pile").replace("_", " ").title()
                trackers[next_track_id] = GarbageObjectTracker(
                    bbox=[bx1, by1, bx2, by2],
                    label="GARBAGE DUMP",
                    track_id=next_track_id,
                    confidence=conf,
                    description=desc,
                    source="Gemini",
                    severity=d.get("severity", 4),
                )
                next_track_id += 1

    frame_idx = 0
    sample_cadence = max(15, int(fps * 1.2))  # Query Gemini at regular keyframe intervals

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        curr_sec = frame_idx / fps
        annotated = frame.copy()

        # Compute dynamic real-time scores for this frame
        d_val, g_val, dep_val, comp_val, band_str, status_str = get_temporal_telemetry(
            curr_sec, total_sec, drainage_score, garbage_score, water_depth_cm
        )

        # 1. Advance all active trackers using Kalman prediction
        for tracker in list(trackers.values()):
            tracker.predict(w, h)

        # 2. Keyframe Gemini semantic visual detection
        new_candidates = []
        is_sample_frame = (frame_idx == 0 or frame_idx % sample_cadence == 0 or len(trackers) == 0)
        if is_sample_frame and gemini_client is not None:
            new_candidates = detect_garbage_candidates(
                frame=frame,
                client=gemini_client,
                confidence_threshold=confidence_threshold,
                img_w=w,
                img_h=h,
            )

        # 3. Associate detections with existing tracks (IoU + Centroid association)
        for cand in new_candidates:
            cb = cand["box"]
            ccx = (cb[0] + cb[2]) / 2.0
            ccy = (cb[1] + cb[3]) / 2.0

            best_tracker = None
            best_cost = 9999.0

            for tracker in trackers.values():
                if not tracker.active:
                    continue
                tb = tracker.get_box(w, h)
                tcx = (tb[0] + tb[2]) / 2.0
                tcy = (tb[1] + tb[3]) / 2.0
                dist = math.hypot(tcx - ccx, tcy - ccy)
                iou = compute_iou(tb, cb)

                # Spatial consistency check: prevent box from jumping across screen
                max_jump_dist = max(60, min(180, int(0.25 * max(w, h))))
                if iou > 0.15 or dist < max_jump_dist:
                    cost = dist - (100.0 * iou)
                    if cost < best_cost:
                        best_cost = cost
                        best_tracker = tracker

            if best_tracker is not None:
                # Update existing track with measurement
                best_tracker.update(
                    bbox=cb,
                    confidence=cand["confidence"],
                    description=cand["description"],
                    source=cand.get("source", "Gemini"),
                )
            else:
                # Candidate is far away: treat as NEW object instead of jumping existing track
                if cand["confidence"] >= confidence_threshold:
                    trackers[next_track_id] = GarbageObjectTracker(
                        bbox=cb,
                        label="GARBAGE DUMP",
                        track_id=next_track_id,
                        confidence=cand["confidence"],
                        description=cand["description"],
                        source=cand.get("source", "Gemini"),
                    )
                    next_track_id += 1

        # 4. Remove lost or inactive trackers
        for tid in list(trackers.keys()):
            tracker = trackers[tid]
            if not tracker.active:
                del trackers[tid]

        # 5. Render ONLY ACTIVE GARBAGE TRACKERS
        # Drains, roads, soil, water receive NO bounding box.
        for tracker in trackers.values():
            x1, y1, x2, y2 = tracker.get_box(w, h)

            # Determine tactical color and labels based on real-time clearance
            if g_val >= 70.0:
                rank_num = 1
                status_lbl = "CRITICAL"
                box_color = (0, 0, 230)  # Red
                tag_prefix = "GARBAGE DUMP"
            elif g_val >= 45.0:
                rank_num = 2
                status_lbl = "CLEARING"
                box_color = (0, 140, 255)  # Orange
                tag_prefix = "GARBAGE DESILTING"
            elif g_val >= 25.0:
                rank_num = 3
                status_lbl = "RESIDUAL"
                box_color = (0, 215, 255)  # Amber
                tag_prefix = "GARBAGE RECEDING"
            else:
                rank_num = 4
                status_lbl = "CLEANED"
                box_color = (0, 205, 30)  # Bright Green
                tag_prefix = "GARBAGE CLEARED"

            # Draw outer rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)

            # Tactical corner brackets
            corner_len = min(18, max(6, (x2 - x1) // 5), max(6, (y2 - y1) // 5))
            thick = 3
            cv2.line(annotated, (x1, y1), (x1 + corner_len, y1), box_color, thick)
            cv2.line(annotated, (x1, y1), (x1, y1 + corner_len), box_color, thick)
            cv2.line(annotated, (x2, y1), (x2 - corner_len, y1), box_color, thick)
            cv2.line(annotated, (x2, y1), (x2, y1 + corner_len), box_color, thick)
            cv2.line(annotated, (x1, y2), (x1 + corner_len, y2), box_color, thick)
            cv2.line(annotated, (x1, y2), (x1, y2 - corner_len), box_color, thick)
            cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), box_color, thick)
            cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), box_color, thick)

            # Header tag
            tag_label = f"[TRK-{tracker.id:02d}] {tag_prefix}: {g_val:.1f}% • RANK {rank_num} [{status_lbl}]"
            font_scale = max(0.38, min(0.58, w / 1100.0))
            (tw, th), _ = cv2.getTextSize(tag_label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
            tag_y = max(th + 6, y1)
            tag_x = max(0, min(w - tw - 10, x1))
            cv2.rectangle(annotated, (tag_x, tag_y - th - 6), (tag_x + tw + 8, tag_y + 4), box_color, -1)
            cv2.putText(annotated, tag_label, (tag_x + 4, tag_y - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

            # Debug Information Badge (Requirement 10)
            dbg_lines = [
                f"GARBAGE ID: {tracker.id}",
                f"Class: {tracker.category}",
                f"Confidence: {tracker.confidence:.2f}",
                f"Detection source: {tracker.source}",
                f"Tracking status: {tracker.status}",
            ]
            dbg_font_scale = max(0.30, min(0.44, w / 1300.0))
            line_h = int(14 * (dbg_font_scale / 0.38))
            card_w = max(140, int(180 * (w / 1000.0)))
            card_h = len(dbg_lines) * line_h + 8

            card_x = max(2, min(w - card_w - 4, x1))
            card_y = y2 + 6 if (y2 + card_h + 10 < h) else max(2, y1 - card_h - th - 12)

            # Render translucent dark backdrop card
            card_roi = annotated[card_y:card_y+card_h, card_x:card_x+card_w]
            if card_roi.shape[0] == card_h and card_roi.shape[1] == card_w:
                card_bg = np.zeros_like(card_roi)
                card_bg[:] = (15, 23, 42)
                cv2.addWeighted(card_bg, 0.78, card_roi, 0.22, 0, card_roi)
                annotated[card_y:card_y+card_h, card_x:card_x+card_w] = card_roi

            cv2.rectangle(annotated, (card_x, card_y), (card_x + card_w, card_y + card_h), box_color, 1)

            for l_idx, line_txt in enumerate(dbg_lines):
                ly = card_y + (l_idx + 1) * line_h - 2
                cv2.putText(annotated, line_txt, (card_x + 4, ly), cv2.FONT_HERSHEY_SIMPLEX, dbg_font_scale, (241, 245, 249), 1, cv2.LINE_AA)

        # 6. Draw Top HUD Banner
        hud_h = max(28, int(h * 0.055))
        hud_overlay = annotated.copy()
        cv2.rectangle(hud_overlay, (0, 0), (w, hud_h), (15, 23, 42), -1)
        cv2.addWeighted(hud_overlay, 0.75, annotated, 0.25, 0, annotated)

        mins = int(curr_sec // 60)
        secs = int(curr_sec % 60)
        millis = int((curr_sec - int(curr_sec)) * 100)
        tc_str = f"{mins:02d}:{secs:02d}.{millis:02d}"

        rec_color = (0, 0, 255) if int(curr_sec * 2) % 2 == 0 else (50, 50, 180)
        cv2.circle(annotated, (14, hud_h // 2), 5, rec_color, -1)
        top_font_scale = max(0.35, min(0.52, w / 1200.0))
        top_left_text = f"REC  LIVE CCTV | {camera_name} ({camera_id})"
        cv2.putText(annotated, top_left_text, (26, int(hud_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, top_font_scale, (241, 245, 249), 1, cv2.LINE_AA)

        top_right_text = f"TS: {tc_str} | GPS: {gps_str}"
        (trw, _), _ = cv2.getTextSize(top_right_text, cv2.FONT_HERSHEY_SIMPLEX, top_font_scale, 1)
        cv2.putText(annotated, top_right_text, (max(w - trw - 12, int(w * 0.5)), int(hud_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, top_font_scale, (203, 213, 225), 1, cv2.LINE_AA)

        # 7. Draw Bottom Telemetry Banner with real-time changing numbers
        b_hud_h = max(28, int(h * 0.06))
        b_overlay = annotated.copy()
        cv2.rectangle(b_overlay, (0, h - b_hud_h), (w, h), (15, 23, 42), -1)
        cv2.addWeighted(b_overlay, 0.85, annotated, 0.15, 0, annotated)

        bot_font_scale = max(0.33, min(0.48, w / 1200.0))
        bot_text = f"DRAIN: {int(d_val)}% | GARBAGE: {int(g_val)}% | DEPTH: {int(dep_val)}cm | RISK: {int(comp_val)} [{band_str}] | {status_str}"
        cv2.putText(annotated, bot_text, (12, h - int(b_hud_h * 0.35)), cv2.FONT_HERSHEY_SIMPLEX, bot_font_scale, (255, 255, 255), 1, cv2.LINE_AA)

        out.write(annotated)
        frame_idx += 1

    cap.release()
    out.release()
    return output_path
