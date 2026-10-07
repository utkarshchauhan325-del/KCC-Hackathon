"""Local detector: result parsing, track aggregation, waste sorting, rendering and scoring."""

from pathlib import Path

import numpy as np
import pytest

from app.config import settings
from app.core.detector import (
    OBJECT_CLASSES, VISUAL_GARBAGE_CLASSES, FrameDetection, VideoObjectSummary, parse_result,
)
from app.core.evidence import generate_annotated_surveillance_video
from app.core.schemas import SewerAssessment
from app.core.scoring import compute_observed_hazard_scores

SAMPLE_VIDEO = Path(__file__).parent / "fixtures" / "sample_cctv.mp4"
ALL_CLASSES = list(OBJECT_CLASSES) + list(VISUAL_GARBAGE_CLASSES.values())
CLS = {c.prompt: c for c in ALL_CLASSES}


def _det(prompt, tid, box=(10, 10, 110, 110), conf=0.8, square=True):
    x1, y1, x2, y2 = box
    poly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32) if square else None
    return FrameDetection(track_id=tid, cls=CLS[prompt], confidence=conf, box=box, contours=[poly] if poly is not None else [])


def test_garbage_comes_only_from_exemplar_classes_with_waste_types():
    assert all(c.category != "garbage" and c.waste_type is None for c in OBJECT_CLASSES)
    for key, c in VISUAL_GARBAGE_CLASSES.items():
        assert c.category == "garbage" and c.waste_type == key and c.prompt == f"vp:{key}"


class _Arr:
    def __init__(self, a):
        self.a = np.asarray(a)

    def cpu(self):
        return self

    def numpy(self):
        return self.a


def test_parse_result_maps_classes_tracks_and_masks():
    idx = [c.prompt for c in ALL_CLASSES].index("vp:dry_plastic")
    boxes = type("B", (), {
        "xyxy": _Arr([[1, 2, 30, 40], [5, 5, 9, 9]]), "cls": _Arr([idx, 999]),
        "conf": _Arr([0.7, 0.9]), "__len__": lambda self: 2,
    })()
    data = np.zeros((2, 50, 50), dtype=np.uint8)
    data[0, 2:20, 2:20] = 1   # mask 0 has two separate pieces...
    data[0, 30:45, 30:45] = 1  # ...which must stay two outlines, not one joined polygon
    import torch
    masks = type("M", (), {"data": torch.from_numpy(data)})()
    result = type("R", (), {"boxes": boxes, "masks": masks, "orig_shape": (50, 50)})()

    dets = parse_result(result, ALL_CLASSES, {0: 7})
    assert len(dets) == 1  # out-of-range class index dropped
    d = dets[0]
    assert d.track_id == 7 and d.cls.label == "plastic waste" and d.cls.waste_type == "dry_plastic"
    assert d.box == (1, 2, 30, 40) and len(d.contours) == 2
    assert sorted(int(c[:, 0].min()) for c in d.contours) == [2, 30]
    assert parse_result(result, ALL_CLASSES)[0].track_id is None  # unconfirmed: drawn without ID


def test_summary_tracks_countables_and_measures_garbage_as_area():
    s = VideoObjectSummary(1000, 1000, min_frames=2)
    # Person track 2 flickers to "bicycle" once; the confidence-weighted majority wins
    s.add(0.0, [_det("person", 2, conf=0.9), _det("vp:wet_organic", None, box=(0, 0, 500, 500)), _det("motorcycle", 4)])
    s.add(0.2, [_det("bicycle", 2, conf=0.3), _det("vp:wet_organic", None, box=(0, 0, 500, 500)),
                _det("vp:dry_plastic", None, box=(250, 0, 750, 500))])  # overlaps food waste by half
    s.add(0.4, [_det("person", 2, conf=0.8), _det("person", 5), _det("person", 6)])
    out = s.to_dict("test-model", exemplar_frames=3)

    objs = {o["track_id"]: o for o in out["objects"]}
    assert set(objs) == {2}  # tracks 4, 5, 6 seen in < min_frames frames
    assert objs[2]["label"] == "person" and objs[2]["first_sec"] == 0.0 and objs[2]["last_sec"] == 0.4
    assert all(o["category"] != "garbage" for o in out["objects"])  # garbage is never tracked
    assert out["counts_by_category"] == {"person": 1}
    assert out["peak_in_frame"]["person"] == 3  # most people in a single frame
    # Coverage is the union of masks: 25% in frame 0, 37.5% in frame 1 (overlap not double-counted)
    assert out["max_garbage_coverage"] == pytest.approx(0.375, abs=0.01)
    assert out["garbage_frame_fraction"] == pytest.approx(2 / 3, abs=0.01)
    share = out["waste_breakdown"]
    assert set(share) == {"wet_organic", "dry_plastic"} and sum(share.values()) == pytest.approx(1.0, abs=0.01)
    assert share["wet_organic"] > share["dry_plastic"]
    assert out["garbage_exemplar_frames"] == 3 and out["min_frames"] == 2
    unmeasured = s.to_dict("test-model", garbage_measured=False)
    assert unmeasured["garbage_coverage"] is None and unmeasured["garbage_measured"] is False
    assert out["timeline"][0]["garbage_coverage"] == pytest.approx(0.375, abs=0.01)


class FakeDetector:
    model_name = "fake"

    def __init__(self):
        self.started = 0
        self.calls = 0
        self.exemplars = ["example"]  # pretend Gemini supplied garbage examples

    def set_exemplars(self, exemplars):
        self.exemplars = exemplars

    def start_video(self):
        self.started += 1

    def track(self, frame):
        self.calls += 1
        h, w = frame.shape[:2]
        return [_det("vp:mixed", None, box=(0, h // 2, w // 2, h)), _det("person", 2, box=(w // 2, 0, w, h // 2))]


def test_render_with_detector_samples_frames_and_summarises(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DETECTOR_FPS", 5.0)
    det = FakeDetector()
    out, summary = generate_annotated_surveillance_video(SAMPLE_VIDEO, tmp_path / "o.mp4", detector=det)
    assert out.stat().st_size > 1000
    assert det.started == 1
    assert 0 < det.calls == summary["frames_analyzed"]
    assert summary["counts_by_category"] == {"person": 1}
    assert summary["waste_breakdown"] == {"mixed": 1.0}
    assert summary["garbage_coverage"] == pytest.approx(0.25, abs=0.02)


def test_select_keyframes_prefers_issue_frames_and_spreads_the_rest():
    from app.core.evidence import select_keyframes
    from app.core.schemas import BBox, InfraIssue

    issue = InfraIssue(category="garbage", subtype="dump_pile", severity=3, start_ts="00:00", end_ts="00:02",
                       best_frame_ts="00:01", box=BBox(ymin=0, xmin=0, ymax=10, xmax=10), description="x", confidence=0.9)
    frames = select_keyframes(SAMPLE_VIDEO, [issue], 3)
    times = [t for t, _ in frames]
    assert len(frames) == 3 and 1.0 in times
    assert all(b - a >= 1.0 for a, b in zip(times, times[1:]))


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
    assert all(d.contours for d in people)
