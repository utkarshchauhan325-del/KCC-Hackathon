"""Evidence extraction, frame annotation, bounding box crops, and privacy blurring."""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Union
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

def select_keyframes(video_path: Union[str, Path], issues: list, max_frames: int) -> List[Tuple[float, np.ndarray]]:
    """Pick up to max_frames frames: Gemini's best frames for garbage/drainage issues first,
    then evenly spaced frames, skipping any within 1 s of one already chosen."""
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    duration = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / fps
    cap.release()
    if duration <= 0 or max_frames <= 0:
        return []
    candidates = [
        timestamp_to_seconds(i.best_frame_ts) for i in issues if i.category in ("garbage", "drainage")
    ]
    candidates += [duration * (k + 0.5) / max_frames for k in range(max_frames)]
    chosen: List[float] = []
    for t in candidates:
        t = min(max(0.0, t), max(0.0, duration - 0.05))
        if len(chosen) < max_frames and all(abs(t - c) >= 1.0 for c in chosen):
            chosen.append(t)
    frames = []
    for t in sorted(chosen):
        frame = extract_frame_at_timestamp(video_path, t)
        if frame is not None:
            frames.append((t, frame))
    return frames


def encode_jpeg(frame: np.ndarray, max_side: int = 1024, quality: int = 85) -> bytes:
    """JPEG-encode a frame, downscaled so its longer side is at most max_side."""
    h, w = frame.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("JPEG encoding failed")
    return buf.tobytes()


def save_image(img: np.ndarray, output_path: Union[str, Path]) -> Path:
    """Save OpenCV BGR image to disk."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), img)
    return out


# BGR colours per object category, and per waste stream for garbage
CATEGORY_COLORS = {
    "garbage": (0, 140, 255),    # orange
    "bin": (180, 180, 180),      # grey
    "drainage": (230, 160, 0),   # blue
    "road": (0, 0, 220),         # red
    "person": (60, 200, 60),     # green
    "vehicle": (200, 80, 200),   # purple
    "plate": (0, 230, 255),      # yellow
}
WASTE_COLORS = {
    "dry_plastic": (255, 180, 60),   # light blue
    "dry_paper": (90, 160, 210),     # tan
    "wet_organic": (40, 160, 40),    # dark green
    "construction": (120, 120, 120), # grey
    "e_waste": (200, 40, 160),       # magenta
    "mixed": (0, 140, 255),          # orange
}


def _draw_tag(img: np.ndarray, text: str, x: int, y: int, color: Tuple[int, int, int], scale: float) -> None:
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    h, w = img.shape[:2]
    x = max(0, min(w - tw - 8, x))
    y = max(th + 6, y)
    cv2.rectangle(img, (x, y - th - 6), (x + tw + 8, y + 3), color, -1)
    cv2.putText(img, text, (x + 4, y - 2), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)


def _det_color(det) -> Tuple[int, int, int]:
    return WASTE_COLORS.get(det.cls.waste_type) or CATEGORY_COLORS.get(det.cls.category, (255, 255, 255))


def draw_detections(frame: np.ndarray, detections: list) -> np.ndarray:
    """Draw per-object segmentation masks, outlines and labels from the local detector."""
    from app.core.detector import WASTE_TYPE_LABELS

    out = frame.copy()
    overlay = frame.copy()
    w = frame.shape[1]
    scale = max(0.35, min(0.55, w / 1300.0))
    for det in detections:
        if det.contours:
            cv2.fillPoly(overlay, det.contours, _det_color(det))
        else:
            x1, y1, x2, y2 = det.box
            cv2.rectangle(overlay, (x1, y1), (x2, y2), _det_color(det), -1)
    cv2.addWeighted(overlay, 0.35, out, 0.65, 0, out)

    for det in detections:
        color = _det_color(det)
        x1, y1, x2, y2 = det.box
        if det.contours:
            cv2.polylines(out, det.contours, True, color, 2, cv2.LINE_AA)
        else:
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        tid = f"#{det.track_id} " if det.track_id is not None else ""
        waste = f" | {WASTE_TYPE_LABELS[det.cls.waste_type]}" if det.cls.waste_type else ""
        _draw_tag(out, f"{tid}{det.cls.label}{waste} {det.confidence:.2f}", x1, y1, color, scale)
    return out


def _draw_vlm_issues(frame: np.ndarray, issues: list, curr_sec: float) -> np.ndarray:
    """Draw Gemini (VLM) findings: its box around the best frame, and a list of issues active now."""
    h, w = frame.shape[:2]
    scale = max(0.35, min(0.5, w / 1300.0))
    active = []
    for issue in issues:
        start, end = timestamp_to_seconds(issue.start_ts), timestamp_to_seconds(issue.end_ts)
        if start - 0.5 <= curr_sec <= end + 0.5:
            active.append(issue)
        # Gemini's box is only valid for its best frame, so show it for one second around it
        if abs(curr_sec - timestamp_to_seconds(issue.best_frame_ts)) <= 0.5:
            x1, y1, x2, y2 = scale_bbox_to_pixels(issue.box, w, h)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
            cv2.rectangle(frame, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), (0, 0, 0), 1)
            _draw_tag(frame, f"VLM: {issue.subtype.replace('_', ' ')} sev {issue.severity}", x1, y2 + 18, (40, 40, 40), scale)

    y = max(28, int(h * 0.055)) + 24
    for issue in active[:5]:
        _draw_tag(frame, f"VLM {issue.category}: {issue.subtype.replace('_', ' ')} (sev {issue.severity})", 8, y, (40, 40, 40), scale)
        y += int(24 * scale / 0.45)
    return frame


def generate_annotated_surveillance_video(
    video_path: Union[str, Path],
    output_path: Union[str, Path],
    vlm_issues: Optional[list] = None,
    camera_meta: Optional[dict] = None,
    detector=None,
    progress_cb=None,
) -> Tuple[Path, Optional[dict]]:
    """Render the evidence video: per-object masks/tracks from the local detector plus Gemini findings.

    Returns the output path and the detector's object summary (None when no detector was used).
    """
    from app.core.detector import VideoObjectSummary, CATEGORY_LABELS, WASTE_TYPE_LABELS

    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vlm_issues = vlm_issues or []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Cannot open video for annotation: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    camera_id = camera_meta.get("id", "CAM-PUNE-01") if camera_meta else "CAM-PUNE-01"
    camera_name = camera_meta.get("name", "CCTV feed") if camera_meta else "CCTV feed"
    gps_str = camera_meta.get("gps", "not set") if camera_meta else "not set"

    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))
    if not out.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

    summary = VideoObjectSummary(w, h, min_frames=max(2, round(settings.DETECTOR_FPS * 0.5))) if detector else None
    stride = max(1, round(fps / settings.DETECTOR_FPS)) if detector else 1
    if detector:
        detector.start_video()

    detections: list = []
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        curr_sec = frame_idx / fps

        if detector and frame_idx % stride == 0:
            detections = detector.track(frame)
            summary.add(curr_sec, detections)
            if progress_cb and total_frames and frame_idx % (stride * 25) == 0:
                progress_cb(f"Segmenting objects: frame {frame_idx}/{total_frames}")

        annotated = draw_detections(frame, detections) if detector else frame.copy()
        annotated = _draw_vlm_issues(annotated, vlm_issues, curr_sec)

        # Top HUD: camera, timecode, GPS
        hud_h = max(28, int(h * 0.055))
        hud = annotated.copy()
        cv2.rectangle(hud, (0, 0), (w, hud_h), (15, 23, 42), -1)
        cv2.addWeighted(hud, 0.75, annotated, 0.25, 0, annotated)
        font = max(0.35, min(0.52, w / 1200.0))
        tc = f"{int(curr_sec // 60):02d}:{curr_sec % 60:05.2f}"
        cv2.putText(annotated, f"{camera_name} ({camera_id})", (12, int(hud_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, font, (241, 245, 249), 1, cv2.LINE_AA)
        right = f"TS {tc} | GPS {gps_str}"
        (rw, _), _ = cv2.getTextSize(right, cv2.FONT_HERSHEY_SIMPLEX, font, 1)
        cv2.putText(annotated, right, (max(w - rw - 12, w // 2), int(hud_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, font, (203, 213, 225), 1, cv2.LINE_AA)

        # Bottom banner: what the detector sees in this frame
        if detector:
            counts: dict = {}
            waste: dict = {}
            for det in detections:
                counts[det.cls.category] = counts.get(det.cls.category, 0) + 1
                if det.cls.waste_type:
                    waste[det.cls.waste_type] = waste.get(det.cls.waste_type, 0) + 1
            parts = [f"{CATEGORY_LABELS[c]} {n}" for c, n in counts.items()]
            text = " | ".join(parts) if parts else "No objects detected in this frame"
            if waste:
                text += "  ||  Waste: " + ", ".join(f"{WASTE_TYPE_LABELS[k]} {n}" for k, n in waste.items())
        else:
            text = "Local detector off: showing LLM model findings only"
        b_h = max(28, int(h * 0.06))
        band = annotated.copy()
        cv2.rectangle(band, (0, h - b_h), (w, h), (15, 23, 42), -1)
        cv2.addWeighted(band, 0.85, annotated, 0.15, 0, annotated)
        bfont = max(0.33, min(0.48, w / 1250.0))
        cv2.putText(annotated, text, (12, h - int(b_h * 0.35)), cv2.FONT_HERSHEY_SIMPLEX, bfont, (255, 255, 255), 1, cv2.LINE_AA)

        out.write(annotated)
        frame_idx += 1

    cap.release()
    out.release()
    if fourcc != cv2.VideoWriter_fourcc(*"avc1"):
        _transcode_to_h264(output_path)
    if not detector:
        return output_path, None
    exemplars = len(getattr(detector, "exemplars", []))
    return output_path, summary.to_dict(detector.model_name, exemplar_frames=exemplars, garbage_measured=exemplars > 0)


def _transcode_to_h264(path: Path) -> None:
    """Re-encode an mp4v file to H.264 in place; browsers cannot play mp4v."""
    import subprocess
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return
    tmp = path.with_name(path.stem + ".h264.mp4")
    proc = subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(path), "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-preset", "veryfast", "-movflags", "+faststart", str(tmp)],
        capture_output=True,
    )
    if proc.returncode == 0 and tmp.is_file():
        tmp.replace(path)
    else:
        tmp.unlink(missing_ok=True)
