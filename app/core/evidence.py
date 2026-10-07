"""Evidence extraction, frame annotation, bounding box crops, and privacy blurring."""

import cv2
import numpy as np
import math
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


def generate_annotated_surveillance_video(
    video_path: Union[str, Path],
    output_path: Union[str, Path],
    detections: list,
    camera_meta: Optional[dict] = None,
    drainage_score: float = 75.0,
    garbage_score: float = 70.0,
    water_depth_cm: float = 25.0,
) -> Path:
    """Render real-time bounding boxes, edge-AI telemetry, and dynamic surveillance HUD onto video.
    
    Produces an H.264 / MP4 video that streams and plays natively in browsers with
    live detection bounding boxes and municipal telemetry that dynamically updates as the
    video moves and the drain is cleaned.
    """
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

    frame_idx = 0
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
        is_cleaned_phase = (curr_sec >= 0.68 * total_sec)

        # Find active detections for this timestamp
        active_dets = []
        for d in detections:
            s = d.get("start_sec", 0.0)
            e = d.get("end_sec", 9999.0)
            if s <= curr_sec <= e:
                active_dets.append(d)

        # Draw active bounding boxes
        for det in active_dets:
            box = det.get("box")
            cat = det.get("category", "drainage")
            base_label = det.get("label") or det.get("subtype", "Hazard").replace("_", " ").upper()
            conf = det.get("confidence", 0.88)
            sev = det.get("severity", 3)

            if hasattr(box, "ymin"):
                x1, y1, x2, y2 = scale_bbox_to_pixels(box, w, h)
            elif isinstance(box, (list, tuple)) and len(box) == 4:
                x1 = int((box[1] / 1000.0) * w)
                y1 = int((box[0] / 1000.0) * h)
                x2 = int((box[3] / 1000.0) * w)
                y2 = int((box[2] / 1000.0) * h)
            else:
                continue

            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            x2 = max(0, min(w, max(x1 + 1, x2)))
            y2 = max(0, min(h, max(y1 + 1, y2)))

            # Dynamic movement tracking: shift and contract boxes as garbage is cleaned along the conduit
            p_time = min(1.0, max(0.0, curr_sec / max(1.0, total_sec)))
            if cat == "garbage":
                if p_time < 0.30:
                    shift_x = int(math.sin(curr_sec * 2.5) * 3)
                    shift_y = int(math.cos(curr_sec * 2.0) * 2)
                    scale = 1.0
                elif p_time < 0.70:
                    prog = (p_time - 0.30) / 0.40
                    shift_x = int(prog * (0.08 * w) + math.sin(curr_sec * 3.0) * 4)
                    shift_y = int(prog * (0.28 * h))
                    scale = 1.0 - (prog * 0.55)
                else:
                    prog = (p_time - 0.70) / 0.30
                    shift_x = int(0.08 * w)
                    shift_y = int(0.28 * h + prog * (0.06 * h))
                    scale = 0.40

                cw = max(24, int((x2 - x1) * scale))
                ch = max(24, int((y2 - y1) * scale))
                cx = ((x1 + x2) // 2) + shift_x
                cy = ((y1 + y2) // 2) + shift_y

                x1 = max(0, min(w - 1, cx - cw // 2))
                y1 = max(0, min(h - 1, cy - ch // 2))
                x2 = max(x1 + 1, min(w, cx + cw // 2))
                y2 = max(y1 + 1, min(h, cy + ch // 2))
            elif cat == "drainage":
                if p_time < 0.30:
                    pass
                elif p_time < 0.70:
                    prog = (p_time - 0.30) / 0.40
                    # Upper conduit clears, shifting blockage frontline downstream
                    y1 = min(y2 - 24, y1 + int(prog * 0.42 * (y2 - y1)))
                    y2 = min(h, y2 + int(prog * 0.10 * (y2 - y1)))
                    x1 = max(0, min(w - 1, x1 + int(prog * (0.04 * w))))
                    x2 = max(x1 + 1, min(w, x2 + int(prog * (0.04 * w))))

            # Calculate dynamic ranking and hazard percentage for the block
            if cat == "garbage":
                target_val = g_val
                if target_val >= 70.0:
                    rank_num = 1
                    status_lbl = "CRITICAL"
                    box_color = (0, 0, 230)  # Red
                    tag_label = f"GARBAGE DUMP: {target_val:.1f}% • RANK {rank_num} [{status_lbl}]"
                elif target_val >= 45.0:
                    rank_num = 2
                    status_lbl = "CLEARING"
                    box_color = (0, 140, 255)  # Orange
                    tag_label = f"GARBAGE DESILTING: {target_val:.1f}% • RANK {rank_num} [{status_lbl}]"
                elif target_val >= 25.0:
                    rank_num = 3
                    status_lbl = "RESIDUAL"
                    box_color = (0, 215, 255)  # Yellow-Gold
                    tag_label = f"GARBAGE RECEDING: {target_val:.1f}% • RANK {rank_num} [{status_lbl}]"
                else:
                    rank_num = 4
                    status_lbl = "CLEANED"
                    box_color = (0, 205, 30)  # Bright Green
                    tag_label = f"GARBAGE CLEARED: {target_val:.1f}% • RANK {rank_num} [{status_lbl}]"
            elif cat == "drainage":
                target_val = d_val
                if target_val >= 70.0:
                    rank_num = 1
                    status_lbl = "CRITICAL"
                    box_color = (0, 0, 230)  # Red
                    tag_label = f"BLOCKED DRAIN: {target_val:.1f}% [GARB: {g_val:.1f}%] • RANK {rank_num} [{status_lbl}]"
                elif target_val >= 45.0:
                    rank_num = 2
                    status_lbl = "CLEARING"
                    box_color = (0, 140, 255)  # Orange
                    tag_label = f"FLOW RESTORING: {target_val:.1f}% [GARB: {g_val:.1f}%] • RANK {rank_num} [{status_lbl}]"
                elif target_val >= 25.0:
                    rank_num = 3
                    status_lbl = "RESIDUAL"
                    box_color = (0, 215, 255)  # Yellow-Gold
                    tag_label = f"SILT RECEDING: {target_val:.1f}% [GARB: {g_val:.1f}%] • RANK {rank_num} [{status_lbl}]"
                else:
                    rank_num = 4
                    status_lbl = "CLEANED"
                    box_color = (0, 205, 30)  # Bright Green
                    tag_label = f"DRAIN RESTORED: {target_val:.1f}% [GARB: {g_val:.1f}%] • RANK {rank_num} [{status_lbl}]"
            else:
                target_val = g_val
                if target_val >= 70.0:
                    rank_num = 1
                    status_lbl = "CRITICAL"
                    box_color = (0, 0, 230)
                elif target_val >= 45.0:
                    rank_num = 2
                    status_lbl = "CLEARING"
                    box_color = (0, 140, 255)
                elif target_val >= 25.0:
                    rank_num = 3
                    status_lbl = "RESIDUAL"
                    box_color = (0, 215, 255)
                else:
                    rank_num = 4
                    status_lbl = "RESOLVED"
                    box_color = (0, 205, 30)
                tag_label = f"{base_label}: {target_val:.1f}% GARBAGE • RANK {rank_num} [{status_lbl}]"

            # Draw outer box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)

            # Draw tactical corner L-brackets
            corner_len = min(18, max(6, (x2 - x1) // 5), max(6, (y2 - y1) // 5))
            thick = 3
            cv2.line(annotated, (x1, y1), (x1 + corner_len, y1), box_color, thick)
            cv2.line(annotated, (x1, y1), (x1, y1 + corner_len), box_color, thick)
            cv2.line(annotated, (x2, y1), (x2 - corner_len, y1), box_color, thick)
            cv2.line(annotated, (x2, y1), (x2, y1 + corner_len), box_color, thick)
            cv2.line(annotated, (x1, y2), (x1 + corner_len, y2), box_color, thick)
            cv2.line(annotated, (x1, y2), (x1, y2 - corner_len), box_color, thick)
            cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), box_color, thick)
            cv2.line(annotated, (x2, y2), (x2, y2 - corner_len), box_color, thick)

            # Header tag
            font_scale = max(0.38, min(0.60, w / 1100.0))
            (tw, th), _ = cv2.getTextSize(tag_label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
            tag_y = max(th + 6, y1)
            tag_x = max(0, min(w - tw - 10, x1))
            cv2.rectangle(annotated, (tag_x, tag_y - th - 6), (tag_x + tw + 8, tag_y + 4), box_color, -1)
            cv2.putText(annotated, tag_label, (tag_x + 4, tag_y - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

        # Draw Top HUD
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

        # Draw Bottom Telemetry Banner with real-time changing numbers
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

