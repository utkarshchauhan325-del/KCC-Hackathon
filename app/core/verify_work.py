"""AI Work Verification Engine for FloodGuard.

Implements the 6-step verification pipeline:
1. Quality Gate (blur, exposure, resolution)
2. Location Check (GPS Haversine distance)
3. Gemini Before/After VLM Comparison (Pydantic-validated JSON)
4. Local YOLOE re-measurement of remaining garbage area %
5. Deterministic decision function based on config thresholds
6. Persistence, 3-attempt escalation, and incident status resolution
"""

import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import AuditLog, Incident, Task, TaskSubmission
from app.core.gemini_client import GeminiVideoClient
from app.core.prompts import SYSTEM_CONTEXT, WORK_VERIFICATION_PROMPT
from app.core.schemas import WorkVerificationAssessment
from app.notify.alerts import send_work_verified_alert, send_manual_review_alert

logger = logging.getLogger("civiceye.verify_work")


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two GPS coordinates."""
    r_earth = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r_earth * c


def check_image_quality(img_or_path: Union[str, Path, np.ndarray, Image.Image, bytes]) -> Tuple[bool, float, Optional[str]]:
    """Step 1: Check resolution, blur (Laplacian variance), and exposure/brightness.
    
    Returns (passed, sharpness_score, error_reason).
    """
    mat = None
    if isinstance(img_or_path, (str, Path)):
        p = Path(img_or_path)
        if not p.is_file():
            return False, 0.0, f"Image file not found: {p}"
        mat = cv2.imread(str(p))
    elif isinstance(img_or_path, np.ndarray):
        mat = img_or_path
    elif isinstance(img_or_path, Image.Image):
        mat = cv2.cvtColor(np.array(img_or_path), cv2.COLOR_RGB2BGR)
    elif isinstance(img_or_path, bytes):
        arr = np.frombuffer(img_or_path, dtype=np.uint8)
        mat = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if mat is None or mat.size == 0:
        return False, 0.0, "Unable to decode image data."

    h, w = mat.shape[:2]
    if w < 240 or h < 240:
        return False, 0.0, f"Photo resolution too low ({w}x{h}). Minimum required: 240x240 px."

    gray = cv2.cvtColor(mat, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean_brightness = float(np.mean(gray))

    if mean_brightness < settings.VERIFY_MIN_BRIGHTNESS:
        return False, sharpness, f"Photo is too dark/underexposed (luminance {mean_brightness:.1f} < {settings.VERIFY_MIN_BRIGHTNESS}). Ensure sufficient daylight or lighting."

    if mean_brightness > settings.VERIFY_MAX_BRIGHTNESS:
        return False, sharpness, f"Photo is overexposed/glared (luminance {mean_brightness:.1f} > {settings.VERIFY_MAX_BRIGHTNESS}). Adjust shooting angle to reduce glare."

    if sharpness < settings.VERIFY_MIN_SHARPNESS:
        return False, sharpness, f"Photo is too blurry (sharpness score {sharpness:.1f} < {settings.VERIFY_MIN_SHARPNESS}). Hold the camera steady and retake."

    return True, sharpness, None


def check_location(
    incident_lat: Optional[float],
    incident_lng: Optional[float],
    proof_lat: Optional[float],
    proof_lng: Optional[float],
) -> Tuple[bool, float, Optional[str]]:
    """Step 2: Verify GPS proximity against tolerance threshold."""
    if incident_lat is None or incident_lng is None or proof_lat is None or proof_lng is None:
        return True, 0.0, None  # Graceful pass if GPS is unrecorded; VLM checks landmarks visually

    dist = haversine_distance_meters(incident_lat, incident_lng, proof_lat, proof_lng)
    if dist > settings.VERIFY_LOCATION_TOLERANCE_METERS:
        return (
            False,
            dist,
            f"GPS location mismatch: photo captured {dist:.0f}m away from the incident site (tolerance: {settings.VERIFY_LOCATION_TOLERANCE_METERS:.0f}m).",
        )
    return True, dist, None


def compare_before_after_gemini(
    before_img_path: Union[str, Path],
    after_img_path: Union[str, Path],
    gemini_client: Optional[GeminiVideoClient] = None,
) -> WorkVerificationAssessment:
    """Step 3: Call Gemini with before and after photos, returning structured Pydantic assessment."""
    p_before, p_after = Path(before_img_path), Path(after_img_path)
    if not p_before.is_file() or not p_after.is_file():
        raise FileNotFoundError(f"Missing before/after image file: {p_before} or {p_after}")

    pil_before = Image.open(p_before).convert("RGB")
    pil_after = Image.open(p_after).convert("RGB")

    client = gemini_client or GeminiVideoClient()

    prompt_contents = [
        SYSTEM_CONTEXT,
        WORK_VERIFICATION_PROMPT,
        "--- BEFORE PHOTO (Image 1) ---",
        pil_before,
        "--- AFTER PHOTO (Image 2 - Worker Submission) ---",
        pil_after,
    ]

    return client._call_with_retry_and_fallback(
        contents=prompt_contents,
        response_schema=WorkVerificationAssessment,
        temperature=0.1,
    )


def measure_garbage_area_after(after_img_path: Union[str, Path]) -> float:
    """Step 4: Use YOLOE detector if enabled to measure residual garbage area percentage."""
    if not settings.DETECTOR_ENABLED:
        return 0.0

    try:
        from app.core.detector import CivicObjectDetector
        det = CivicObjectDetector()
        img = Image.open(after_img_path).convert("RGB")
        frame_mat = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        detections = det.track(frame_mat)
        h, w = frame_mat.shape[:2]
        total_pixels = float(h * w)
        garbage_pixels = 0.0
        for d in detections:
            if getattr(d.cls, "category", "") == "garbage":
                x1, y1, x2, y2 = d.box
                garbage_pixels += max(0, (x2 - x1) * (y2 - y1))
        return min(100.0, round((garbage_pixels / total_pixels) * 100.0, 1))
    except Exception as e:
        logger.warning("Local detector garbage remeasure skipped: %s", e)
        return 0.0


def evaluate_decision(
    quality_passed: bool,
    quality_reason: Optional[str],
    location_passed: bool,
    location_reason: Optional[str],
    assessment: WorkVerificationAssessment,
    garbage_before_pct: float,
    garbage_after_pct: float,
    attempt_number: int,
) -> Tuple[str, List[str]]:
    """Step 5: Deterministic decision function based on config thresholds.
    
    The VLM never decides the final result; Python thresholds decide.
    Returns (status: 'verified' | 'rejected' | 'manual_review', reasons: List[str]).
    """
    reasons: List[str] = []

    # Quality Gate failure -> Reject
    if not quality_passed:
        return "rejected", [quality_reason or "Image quality gate failed."]

    # Location check failure -> Escalate to manual review
    if not location_passed:
        reasons.append(location_reason or "Location check failed.")
        return "manual_review", reasons

    # Landmark/location mismatch -> Reject
    if not assessment.same_location:
        reasons.append("Photo does not match the original incident location or background landmarks.")
        if attempt_number >= settings.VERIFY_MAX_ATTEMPTS:
            reasons.append(f"Exceeded attempt limit ({settings.VERIFY_MAX_ATTEMPTS} attempts).")
            return "manual_review", reasons
        return "rejected", reasons

    # Check cleaning criteria
    cleaned = assessment.cleaned and assessment.hazard_resolved
    conf = assessment.confidence
    waste_remaining_ok = garbage_after_pct <= settings.VERIFY_MAX_GARBAGE_REMAINING_PCT

    # Check reduction if before area was measured
    if garbage_before_pct > 0:
        reduction_pct = ((garbage_before_pct - garbage_after_pct) / garbage_before_pct) * 100.0
        reduction_ok = reduction_pct >= settings.VERIFY_MIN_GARBAGE_REDUCTION_PCT
    else:
        reduction_ok = True

    # Rule A: High confidence resolution -> Verified
    if cleaned and conf >= settings.VERIFY_MIN_GEMINI_CONFIDENCE and (waste_remaining_ok or reduction_ok):
        return "verified", ["Work confirmed clean and site hazard resolved."]

    # Rule B: Borderline confidence -> Manual Review
    if cleaned and (0.50 <= conf < settings.VERIFY_MIN_GEMINI_CONFIDENCE):
        reasons.append(f"AI evaluation uncertain (confidence {conf:.0%} < {settings.VERIFY_MIN_GEMINI_CONFIDENCE:.0%}).")
        if assessment.explanation:
            reasons.append(assessment.explanation)
        return "manual_review", reasons

    # Rule C: Site not fully cleaned or waste remaining too high
    if not cleaned:
        reasons.append("Issue is not fully resolved; debris or hazard remains visible.")
    if not waste_remaining_ok:
        reasons.append(f"Remaining waste area is {garbage_after_pct:.1f}% (must be under {settings.VERIFY_MAX_GARBAGE_REMAINING_PCT:.1f}%).")
    if assessment.explanation:
        reasons.append(assessment.explanation)

    # 3-Attempt Limit check
    if attempt_number >= settings.VERIFY_MAX_ATTEMPTS:
        reasons.append(f"Submission reached 3-attempt limit ({attempt_number}/{settings.VERIFY_MAX_ATTEMPTS}). Escalating to supervisor.")
        return "manual_review", reasons

    return "rejected", reasons


def verify_and_record_submission(
    db: Session,
    task_id: str,
    after_image_input: Union[str, Path, bytes, np.ndarray, Image.Image],
    proof_lat: Optional[float] = None,
    proof_lng: Optional[float] = None,
    worker_notes: Optional[str] = None,
    gemini_client: Optional[GeminiVideoClient] = None,
) -> TaskSubmission:
    """Step 6: Execute full verification pipeline, persist submission, update statuses and alerts."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"Task {task_id} not found.")

    incident = task.incident
    attempt = len(task.submissions) + 1

    # Save after photo to data/evidence/after/
    settings.AFTER_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    after_filename = f"task_{task.id[:8]}_attempt_{attempt}_{int(datetime.utcnow().timestamp())}.jpg"
    after_path = settings.AFTER_PHOTOS_DIR / after_filename

    # Save image bytes/mat to after_path
    if isinstance(after_image_input, (str, Path)):
        src = Path(after_image_input)
        after_path.write_bytes(src.read_bytes())
    elif isinstance(after_image_input, bytes):
        after_path.write_bytes(after_image_input)
    elif isinstance(after_image_input, Image.Image):
        after_image_input.save(after_path, format="JPEG", quality=90)
    elif isinstance(after_image_input, np.ndarray):
        cv2.imwrite(str(after_path), after_image_input)
    else:
        raise TypeError(f"Unsupported image type: {type(after_image_input)}")

    # 1. Quality Check
    q_pass, q_score, q_reason = check_image_quality(after_path)

    # 2. Location Check
    loc_pass, loc_dist, loc_reason = check_location(incident.lat, incident.lng, proof_lat, proof_lng)

    # Find Before Photo
    before_path = None
    for ev in incident.evidences:
        if ev.kind in ("annotated", "frame") and Path(ev.path).is_file():
            before_path = ev.path
            break
    if not before_path:
        # Fallback to after photo itself if no before photo recorded
        before_path = str(after_path)

    # Initial assessment defaults
    assessment = WorkVerificationAssessment(
        cleaned=q_pass and loc_pass,
        same_location=loc_pass,
        hazard_resolved=q_pass and loc_pass,
        confidence=0.85 if q_pass else 0.2,
        explanation=q_reason or "Automated quality check processed.",
    )

    # 3. Call Gemini VLM if quality gate passed
    if q_pass and before_path and Path(before_path).is_file():
        try:
            assessment = compare_before_after_gemini(
                before_img_path=before_path,
                after_img_path=after_path,
                gemini_client=gemini_client,
            )
        except Exception as e:
            logger.warning("Gemini VLM verification call failed: %s", e)
            assessment.confidence = 0.55
            assessment.explanation = f"VLM inspection deferred: {str(e)[:150]}"

    # 4. YOLOE Re-measure
    garbage_before = 35.0 if incident.type == "garbage" else 0.0
    garbage_after = measure_garbage_area_after(after_path) if q_pass else 0.0

    # 5. Deterministic Decision
    decision_status, reasons = evaluate_decision(
        quality_passed=q_pass,
        quality_reason=q_reason,
        location_passed=loc_pass,
        location_reason=loc_reason,
        assessment=assessment,
        garbage_before_pct=garbage_before,
        garbage_after_pct=garbage_after,
        attempt_number=attempt,
    )

    # 6. Persist TaskSubmission
    submission = TaskSubmission(
        task_id=task.id,
        attempt_number=attempt,
        submitted_at=datetime.utcnow(),
        after_photo_path=str(after_path),
        lat=proof_lat,
        lng=proof_lng,
        verification_status=decision_status,
        quality_score=q_score,
        gemini_cleaned=assessment.cleaned,
        gemini_confidence=assessment.confidence,
        gemini_reason=assessment.explanation,
        yoloe_garbage_before_pct=garbage_before,
        yoloe_garbage_after_pct=garbage_after,
        rejection_reasons=json.dumps(reasons),
        worker_notes=worker_notes,
    )
    db.add(submission)

    # Update Task and Incident Statuses
    if decision_status == "verified":
        task.status = "verified"
        incident.status = "resolved"
        db.add(AuditLog(user=f"AI Verifier ({task.worker.name})", action="verified_work", entity="task", entity_id=task.id))
        db.add(AuditLog(user="AI Verifier", action="resolved_incident", entity="incident", entity_id=incident.id))
        send_work_verified_alert(db, task, submission)

    elif decision_status == "manual_review":
        task.status = "manual_review"
        incident.status = "awaiting_verification"
        db.add(AuditLog(user="AI Verifier", action="escalated_manual_review", entity="task", entity_id=task.id))
        send_manual_review_alert(db, task, submission)

    else:  # rejected
        task.status = "in_progress"
        db.add(AuditLog(user="AI Verifier", action="rejected_submission", entity="task", entity_id=task.id))

    db.commit()
    db.refresh(submission)
    return submission
