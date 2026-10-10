"""Tests for worker authentication, site verification pipeline, and resolution rules."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import cv2
import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.schemas import WorkVerificationAssessment
from app.core.verify_work import (
    check_image_quality,
    check_location,
    evaluate_decision,
    verify_and_record_submission,
)
from app.db.models import Base, Incident, Job, Task, TaskSubmission, Worker, hash_password, verify_password
from app.ui.views.login import authenticate_user


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def synthetic_images(tmp_path):
    """Generate sharp, blurry, and dark test images."""
    np.random.seed(42)
    # Sharp image with varied texture
    sharp_img = np.random.randint(60, 200, (400, 400, 3), dtype=np.uint8)
    sharp_path = tmp_path / "sharp.jpg"
    cv2.imwrite(str(sharp_path), sharp_img, [cv2.IMWRITE_JPEG_QUALITY, 95])

    # Blurry image
    blurry_img = cv2.GaussianBlur(sharp_img, (55, 55), 0)
    blurry_path = tmp_path / "blurry.jpg"
    cv2.imwrite(str(blurry_path), blurry_img)

    # Dark image
    dark_img = np.ones((400, 400, 3), dtype=np.uint8) * 10
    dark_path = tmp_path / "dark.jpg"
    cv2.imwrite(str(dark_path), dark_img)

    # Tiny image
    tiny_img = np.zeros((100, 100, 3), dtype=np.uint8)
    tiny_path = tmp_path / "tiny.jpg"
    cv2.imwrite(str(tiny_path), tiny_img)

    return {
        "sharp": sharp_path,
        "blurry": blurry_path,
        "dark": dark_path,
        "tiny": tiny_path,
    }


def test_worker_password_hashing_and_auth():
    """Worker passwords must use salted hashing and verify correctly."""
    pw = "workerSecure123"
    hashed = hash_password(pw)
    assert ":" in hashed
    assert verify_password(pw, hashed) is True
    assert verify_password("wrongPassword", hashed) is False


def test_quality_gate(synthetic_images):
    """Quality gate rejects blurry, underexposed, or undersized photos."""
    # Sharp image passes
    ok, score, reason = check_image_quality(synthetic_images["sharp"])
    assert ok is True
    assert reason is None
    assert score > 0

    # Blurry image fails
    ok, score, reason = check_image_quality(synthetic_images["blurry"])
    assert ok is False
    assert "blurry" in reason.lower()

    # Dark image fails
    ok, score, reason = check_image_quality(synthetic_images["dark"])
    assert ok is False
    assert "dark" in reason.lower() or "lighting" in reason.lower()

    # Tiny image fails
    ok, score, reason = check_image_quality(synthetic_images["tiny"])
    assert ok is False
    assert "resolution" in reason.lower()


def test_location_check():
    """Location check verifies proximity within configurable tolerance."""
    # Same location (Pune Alka Talkies)
    pune_lat, pune_lng = 18.5158, 73.8431
    ok, dist, reason = check_location(pune_lat, pune_lng, pune_lat + 0.0001, pune_lng + 0.0001)
    assert ok is True
    assert dist < settings.VERIFY_LOCATION_TOLERANCE_METERS

    # Far location (> 2 km away)
    ok, dist, reason = check_location(pune_lat, pune_lng, 18.5500, 73.8800)
    assert ok is False
    assert "away" in reason


def test_deterministic_decision_rules():
    """Deterministic evaluation decides verified vs rejected vs manual review."""
    assessment_clean = WorkVerificationAssessment(
        cleaned=True,
        same_location=True,
        hazard_resolved=True,
        confidence=0.92,
        explanation="Site completely free of silt and waste.",
    )

    # 1. Cleaned with low residual waste -> VERIFIED
    status, reasons = evaluate_decision(
        quality_passed=True,
        quality_reason=None,
        location_passed=True,
        location_reason=None,
        assessment=assessment_clean,
        garbage_before_pct=40.0,
        garbage_after_pct=3.0,
        attempt_number=1,
    )
    assert status == "verified"

    # 2. Borderline confidence -> MANUAL_REVIEW
    borderline_assessment = WorkVerificationAssessment(
        cleaned=True,
        same_location=True,
        hazard_resolved=True,
        confidence=0.65,
        explanation="Debris partially cleared but lighting is dim.",
    )
    status, reasons = evaluate_decision(
        quality_passed=True,
        quality_reason=None,
        location_passed=True,
        location_reason=None,
        assessment=borderline_assessment,
        garbage_before_pct=40.0,
        garbage_after_pct=5.0,
        attempt_number=1,
    )
    assert status == "manual_review"

    # 3. Not cleaned on attempt 1 -> REJECTED with retake guidance
    unclean_assessment = WorkVerificationAssessment(
        cleaned=False,
        same_location=True,
        hazard_resolved=False,
        confidence=0.88,
        explanation="Large pile of solid waste still blocking culvert.",
    )
    status, reasons = evaluate_decision(
        quality_passed=True,
        quality_reason=None,
        location_passed=True,
        location_reason=None,
        assessment=unclean_assessment,
        garbage_before_pct=40.0,
        garbage_after_pct=28.0,
        attempt_number=1,
    )
    assert status == "rejected"

    # 4. Attempt 3 failure escalates to MANUAL_REVIEW
    status, reasons = evaluate_decision(
        quality_passed=True,
        quality_reason=None,
        location_passed=True,
        location_reason=None,
        assessment=unclean_assessment,
        garbage_before_pct=40.0,
        garbage_after_pct=28.0,
        attempt_number=3,
    )
    assert status == "manual_review"
    assert any("3-attempt limit" in r for r in reasons)


def test_verify_and_record_submission_lifecycle(test_db, synthetic_images):
    """End-to-end verification pipeline persists submission and triggers state transitions."""
    # Setup worker, job, incident, and task
    worker = Worker(
        id="w-test-1",
        name="Santosh Shinde",
        phone="9820011002",
        email="santosh@pune.gov.in",
        password_hash=hash_password("worker123"),
        zone="Central",
    )
    job = Job(id="job-test-1", filename="cctv_sample.mp4", status="completed")
    incident = Incident(
        id="inc-test-1",
        job_id=job.id,
        type="garbage",
        subtype="dump_pile",
        severity=4,
        status="assigned",
        description="Garbage overflowing near stormwater drain",
        video_ts="00:05",
        lat=18.5204,
        lng=73.8567,
    )
    task = Task(
        id="task-test-1",
        incident_id=incident.id,
        worker_id=worker.id,
        priority="high",
        status="assigned",
    )
    test_db.add_all([worker, job, incident, task])
    test_db.commit()

    # Mock Gemini VLM and YOLOE
    mock_assessment = WorkVerificationAssessment(
        cleaned=True,
        same_location=True,
        hazard_resolved=True,
        confidence=0.90,
        explanation="Waste cleared completely.",
    )

    with patch("app.core.verify_work.compare_before_after_gemini", return_value=mock_assessment), \
         patch("app.core.verify_work.measure_garbage_area_after", return_value=2.0), \
         patch("app.core.verify_work.send_work_verified_alert") as mock_alert:

        sub = verify_and_record_submission(
            db=test_db,
            task_id=task.id,
            after_image_input=synthetic_images["sharp"],
            proof_lat=18.5204,
            proof_lng=73.8567,
            worker_notes="Removed all plastic and debris.",
        )

        assert sub.verification_status == "verified"
        assert sub.attempt_number == 1
        assert task.status == "verified"
        # Crucial Resolve Rule: Incident becomes resolved upon verification
        assert incident.status == "resolved"
        assert mock_alert.called
