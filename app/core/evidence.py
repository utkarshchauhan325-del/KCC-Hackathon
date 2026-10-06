"""Evidence extraction, frame annotation, bounding box crops, and privacy blurring."""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Union
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
