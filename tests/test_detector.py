"""Local detector: result parsing, track aggregation, waste sorting, rendering and scoring."""

from pathlib import Path

import numpy as np
import pytest

from app.config import settings
from app.core.detector import (
    OBJECT_CLASSES, FrameDetection, VideoObjectSummary, parse_result,
)
from app.core.evidence import generate_annotated_surveillance_video
from app.core.schemas import SewerAssessment
from app.core.scoring import compute_observed_hazard_scores

SAMPLE_VIDEO = Path(__file__).parent / "fixtures" / "sample_cctv.mp4"
CLS = {c.prompt: c for c in OBJECT_CLASSES}


def _det(prompt, tid, box=(10, 10, 110, 110), conf=0.8, square=True):
    x1, y1, x2, y2 = box
    poly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32) if square else None
    return FrameDetection(track_id=tid, cls=CLS[prompt], confidence=conf, box=box, polygon=poly)


def test_every_garbage_class_has_a_waste_type():
    for c in OBJECT_CLASSES:
        assert (c.waste_type is not None) == (c.category == "garbage"), c.prompt


class _Arr:
    def __init__(self, a):
        self.a = np.asarray(a)

    def cpu(self):
        return self

    def numpy(self):
        return self.a


def test_parse_result_maps_classes_ids_and_masks():
    idx = [c.prompt for c in OBJECT_CLASSES].index("plastic bag")
    boxes = type("B", (), {
        "xyxy": _Arr([[1, 2, 30, 40], [5, 5, 9, 9]]), "cls": _Arr([idx, 999]),
        "conf": _Arr([0.7, 0.9]), "id": _Arr([7, 8]), "__len__": lambda self: 2,
    })()
    masks = type("M", (), {"xy": [np.array([[1, 2], [30, 2], [30, 40]], dtype=np.float32), None]})()
    result = type("R", (), {"boxes": boxes, "masks": masks})()

    dets = parse_result(result)
    assert len(dets) == 1  # out-of-range class index dropped
    d = dets[0]
    assert d.track_id == 7 and d.cls.label == "plastic bag" and d.cls.waste_type == "dry_plastic"
    assert d.box == (1, 2, 30, 40) and d.polygon.shape == (3, 2)


def test_summary_majority_vote_flicker_filter_and_waste_breakdown():
    s = VideoObjectSummary(1000, 1000)
    # Track 1 flickers between classes; "food waste" wins on confidence-weighted votes
    s.add(0.0, [_det("food waste", 1, conf=0.9), _det("person", 2), _det("plastic bottle", 3)])
    s.add(0.2, [_det("garbage pile", 1, conf=0.4), _det("person", 2)])
    s.add(0.4, [_det("food waste", 1, conf=0.8), _det("motorcycle", 4)])  # track 4 seen once
    out = s.to_dict("test-model")

    objs = {o["track_id"]: o for o in out["objects"]}
    assert set(objs) == {1, 2}  # tracks 3 and 4 seen in < MIN_FRAMES frames
    assert objs[1]["label"] == "food waste" and objs[1]["waste_type"] == "wet_organic"
    assert objs[1]["first_sec"] == 0.0 and objs[1]["last_sec"] == 0.4
    assert out["counts_by_category"] == {"garbage": 1, "person": 1}
    assert out["waste_breakdown"] == {"wet_organic": 1}
    # largest garbage mask coverage in any frame: two 100x100 squares on a 1000x1000 frame
    assert out["max_garbage_coverage"] == pytest.approx(0.02)
    assert out["timeline"][0]["sec"] == 0 and out["timeline"][0]["garbage"] == 2


class FakeDetector:
    model_name = "fake"

    def __init__(self):
        self.started = 0
        self.calls = 0

    def start_video(self):
        self.started += 1

    def track(self, frame):
        self.calls += 1
        h, w = frame.shape[:2]
        return [_det("garbage pile", 1, box=(0, h // 2, w // 2, h)), _det("person", 2, box=(w // 2, 0, w, h // 2))]


def test_render_with_detector_samples_frames_and_summarises(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DETECTOR_FPS", 5.0)
    det = FakeDetector()
    out, summary = generate_annotated_surveillance_video(SAMPLE_VIDEO, tmp_path / "o.mp4", detector=det)
    assert out.stat().st_size > 1000
    assert det.started == 1
    assert 0 < det.calls == summary["frames_analyzed"]
    assert summary["counts_by_category"] == {"garbage": 1, "person": 1}
    assert summary["waste_breakdown"] == {"mixed": 1}
    assert summary["max_garbage_coverage"] == pytest.approx(0.25, abs=0.01)


def _assessment(**kw):
    base = dict(
        water_level="none", water_reaching_road=False, trash_inside="none", trash_near="none",
        grating_covered=False, cover_missing_or_broken=False, wet_conditions=False, confidence=0.9,
    )
    base.update(kw)
    return SewerAssessment(**base)


def test_scores_are_zero_when_nothing_observed():
    r = compute_observed_hazard_scores([], dumping_detected=False, garbage_coverage=0.0)
    assert r["drainage_score"] is None and r["drainage_band"] == "Not assessed"
    assert r["garbage_score"] == 0.0 and r["composite_score"] == 0.0


def test_scores_use_worst_drain_and_detector_coverage():
    r = compute_observed_hazard_scores(
        [_assessment(water_level="pooling"), _assessment(water_level="flowing_over", grating_covered=True, trash_inside="heavy")],
        dumping_detected=True,
        garbage_coverage=0.12,
    )
    assert r["drainage_score"] >= 70.0  # flowing_over floor
    f = r["garbage_breakdown"]["factors"]
    assert f["trash_inside"]["val"] == "heavy"
    assert f["debris_volume"]["val"] == "heavy"
    assert f["trash_near"]["val"] == "heavy"
    assert f["dumping_detected"]["val"] is True
    assert "local detector" in r["score_sources"]["debris_volume"]


def test_scores_fall_back_to_gemini_severity_without_detector():
    r = compute_observed_hazard_scores([], dumping_detected=False, garbage_coverage=None, vlm_garbage_severity=4)
    assert r["garbage_breakdown"]["factors"]["debris_volume"]["val"] == "heavy"
    assert "Gemini" in r["score_sources"]["debris_volume"]


def _baked_model_available() -> bool:
    try:
        import ultralytics  # noqa: F401
    except ImportError:
        return False
    return any(settings.MODELS_DIR.glob("civiceye-*.pt"))


@pytest.mark.skipif(not _baked_model_available(), reason="run scripts/prepare_detector.py to enable")
def test_real_yoloe_segments_people_on_street_photo():
    import cv2
    import ultralytics
    from app.core.detector import CivicObjectDetector

    img = cv2.imread(str(Path(ultralytics.__file__).parent / "assets" / "bus.jpg"))
    det = CivicObjectDetector()
    det.start_video()
    dets = det.track(img)
    people = [d for d in dets if d.cls.category == "person"]
    assert len(people) >= 3
    assert all(d.polygon is not None for d in people)
