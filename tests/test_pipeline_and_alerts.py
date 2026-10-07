"""Pipeline evidence, alerting and violation-approval flow, with Gemini and network mocked."""

from pathlib import Path
from unittest import mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core import pipeline as pipeline_mod
from app.core.plates import is_valid_indian_plate
from app.core.schemas import (
    BBox, InfraIssue, InfraAnalysisResponse, ViolatorEvent, ViolatorAnalysisResponse,
)
from app.db.models import Base, Incident, Evidence, Violation, AlertLog
from app.notify import alerts

SAMPLE_VIDEO = Path(__file__).parent / "fixtures" / "sample_cctv.mp4"


@pytest.fixture
def session_factory(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(pipeline_mod, "SessionLocal", factory)
    monkeypatch.setattr(settings, "EVIDENCE_DIR", tmp_path)
    monkeypatch.setattr(settings, "DETECTOR_ENABLED", False)
    return factory


def _fake_client(issues, events):
    client = mock.Mock()
    client.upload_video.return_value = mock.Mock(name="files/abc")
    client.analyze_infrastructure.return_value = InfraAnalysisResponse(issues=issues)
    client.analyze_violators.return_value = ViolatorAnalysisResponse(events=events)
    client.assess_sewer_point.side_effect = RuntimeError("not needed")
    return client


POTHOLE = InfraIssue(
    category="road", subtype="pothole", severity=4, start_ts="00:00", end_ts="00:02",
    best_frame_ts="00:01", box=BBox(ymin=500, xmin=200, ymax=800, xmax=600),
    description="Deep pothole in left lane.", confidence=0.9,
)
LITTER = InfraIssue(
    category="garbage", subtype="scattered_litter", severity=1, start_ts="00:00", end_ts="00:02",
    best_frame_ts="00:01", box=BBox(ymin=100, xmin=100, ymax=200, xmax=200),
    description="A few wrappers.", confidence=0.6,
)
DUMPING = ViolatorEvent(
    act_ts="00:01", best_frame_ts="00:01",
    person_box=BBox(ymin=200, xmin=100, ymax=900, xmax=300),
    garbage_box=BBox(ymin=700, xmin=300, ymax=900, xmax=400),
    vehicle_box=BBox(ymin=400, xmin=500, ymax=900, xmax=900),
    vehicle_type="two-wheeler", plate_text="MH 12 QX 4821",
    plate_box=BBox(ymin=800, xmin=650, ymax=860, xmax=750), plate_legibility="clear",
    description="Rider in red jacket drops a garbage bag onto the footpath.", confidence=0.85,
)


@pytest.mark.parametrize("plate,valid", [
    ("MH 12 QX 4821", True), ("dl3cab1234", True), ("KA-01-A-0001", True),
    ("22 BH 1234 AA", True), ("MH12", False), ("", False), (None, False),
])
def test_indian_plate_validation(plate, valid):
    assert is_valid_indian_plate(plate) is valid


def test_upload_failure_fails_job_instead_of_inventing_hazards(session_factory):
    client = _fake_client([], [])
    client.upload_video.side_effect = RuntimeError("quota exhausted")
    with pytest.raises(RuntimeError):
        pipeline_mod.CivicEyePipeline(client=client).process_video(SAMPLE_VIDEO)
    db = session_factory()
    assert db.query(Incident).count() == 0


def test_clean_video_produces_no_incidents(session_factory, monkeypatch):
    monkeypatch.setattr(alerts, "configured_channels", lambda: [])
    result = pipeline_mod.CivicEyePipeline(client=_fake_client([], [])).process_video(SAMPLE_VIDEO, run_pass_b=False)
    assert result["incidents_count"] == 0
    assert session_factory().query(Incident).count() == 0


def test_hazards_alert_immediately_and_violations_wait_for_approval(session_factory, monkeypatch):
    sent = []
    monkeypatch.setattr(alerts, "configured_channels", lambda: ["webhook"])
    monkeypatch.setattr(alerts, "send_webhook", lambda payload, files: sent.append((payload, files)) or "HTTP 200")

    pipeline_mod.CivicEyePipeline(client=_fake_client([POTHOLE, LITTER], [DUMPING])).process_video(
        SAMPLE_VIDEO, source_gps="18.52, 73.85"
    )

    db = session_factory()
    # Only the severity-4 pothole is alerted; severity-1 litter is below ALERT_MIN_SEVERITY,
    # and the dumping violation is held for review.
    assert [p["subtype"] for p, _ in sent] == ["pothole"]
    assert sent[0][0]["kind"] == "hazard" and len(sent[0][1]) == 1
    assert db.query(AlertLog).count() == 1

    violation = db.query(Violation).one()
    assert violation.review_status == "pending_review"
    assert violation.plate_valid is True
    kinds = {e.kind for e in db.query(Evidence).filter(Evidence.incident_id == violation.incident_id)}
    assert kinds == {"frame", "crop_person", "crop_vehicle", "crop_plate"}

    # Officer approves -> full evidence pack goes out
    from app.ui.views import priority_queue
    monkeypatch.setattr(priority_queue, "SessionLocal", session_factory)
    results = priority_queue._review_violation(violation.id, "approved", "S. Patil")
    assert results == [("webhook", "sent", "HTTP 200")]
    payload, files = sent[-1]
    assert payload["kind"] == "violation" and payload["plate_text"] == "MH 12 QX 4821"
    assert payload["reviewed_by"] == "S. Patil"
    assert len(files) == 4

    db.expire_all()
    assert db.query(Violation).one().review_status == "approved"


def test_rejected_violation_sends_nothing(session_factory, monkeypatch):
    sent = []
    monkeypatch.setattr(alerts, "configured_channels", lambda: ["webhook"])
    monkeypatch.setattr(alerts, "send_webhook", lambda payload, files: sent.append(payload) or "HTTP 200")
    pipeline_mod.CivicEyePipeline(client=_fake_client([], [DUMPING])).process_video(SAMPLE_VIDEO)

    from app.ui.views import priority_queue
    monkeypatch.setattr(priority_queue, "SessionLocal", session_factory)
    violation = session_factory().query(Violation).one()
    assert priority_queue._review_violation(violation.id, "rejected", "S. Patil") == []
    assert sent == []


def test_failed_channel_is_logged_not_raised(session_factory, monkeypatch):
    monkeypatch.setattr(alerts, "configured_channels", lambda: ["telegram"])
    monkeypatch.setattr(alerts, "send_telegram", mock.Mock(side_effect=ConnectionError("no network")))
    pipeline_mod.CivicEyePipeline(client=_fake_client([POTHOLE], [])).process_video(SAMPLE_VIDEO, run_pass_b=False)
    log = session_factory().query(AlertLog).one()
    assert log.status == "failed" and "no network" in log.response


def test_detector_objects_are_saved_and_drive_garbage_score(session_factory, monkeypatch):
    from tests.test_detector import FakeDetector

    monkeypatch.setattr(alerts, "configured_channels", lambda: [])
    result = pipeline_mod.CivicEyePipeline(client=_fake_client([], []), detector=FakeDetector()).process_video(
        SAMPLE_VIDEO, run_pass_b=False
    )
    assert result["objects"]["counts_by_category"] == {"garbage": 1, "person": 1}
    assert (settings.EVIDENCE_DIR / result["job_id"] / "result.json").is_file()
    assert result["drainage_score"] is None
    assert result["garbage_breakdown"]["factors"]["debris_volume"]["val"] == "massive"


def test_detector_crash_falls_back_to_gemini_only_video(session_factory, monkeypatch):
    from tests.test_detector import FakeDetector

    broken = FakeDetector()
    broken.track = mock.Mock(side_effect=RuntimeError("CUDA out of memory"))
    monkeypatch.setattr(alerts, "configured_channels", lambda: [])
    msgs = []
    result = pipeline_mod.CivicEyePipeline(client=_fake_client([POTHOLE], []), detector=broken).process_video(
        SAMPLE_VIDEO, run_pass_b=False, progress_cb=msgs.append
    )
    assert result["objects"] is None
    assert Path(result["annotated_video_path"]).is_file()
    assert any("Local detector failed" in m for m in msgs)
