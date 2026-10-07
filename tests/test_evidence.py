import pytest
import numpy as np
from pathlib import Path
from app.core.schemas import BBox
from app.core.evidence import (
    timestamp_to_seconds,
    scale_bbox_to_pixels,
    annotate_frame,
    crop_bbox,
    extract_frame_at_timestamp,
    blur_bystander_faces,
)

def test_timestamp_to_seconds():
    assert timestamp_to_seconds("00:15") == 15.0
    assert timestamp_to_seconds("01:30") == 90.0
    assert timestamp_to_seconds("01:02:03") == 3723.0
    assert timestamp_to_seconds("45") == 45.0

def test_scale_bbox_to_pixels():
    box = BBox(ymin=100, xmin=200, ymax=500, xmax=600)
    x1, y1, x2, y2 = scale_bbox_to_pixels(box, img_width=1000, img_height=500)
    assert (x1, y1, x2, y2) == (200, 50, 600, 250)

def test_extract_frame_from_fixture():
    fixture_path = Path("tests/fixtures/sample_cctv.mp4")
    assert fixture_path.exists()
    frame = extract_frame_at_timestamp(fixture_path, ts_seconds=2.0)
    assert frame is not None
    assert frame.shape == (480, 640, 3)

def test_annotate_and_crop():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    box = BBox(ymin=100, xmin=100, ymax=500, xmax=500)
    annotated = annotate_frame(frame, box, label="pothole", severity=4)
    assert annotated.shape == (480, 640, 3)

    crop = crop_bbox(frame, box)
    assert crop.shape[0] > 0 and crop.shape[1] > 0

def test_bystander_face_blur():
    frame = np.full((300, 300, 3), 120, dtype=np.uint8)
    # Does not crash on arbitrary synthetic frames
    blurred = blur_bystander_faces(frame, primary_box=None)
    assert blurred.shape == frame.shape

def test_generate_annotated_surveillance_video(tmp_path):
    from app.core.evidence import generate_annotated_surveillance_video
    fixture_path = Path("tests/fixtures/sample_cctv.mp4")
    out_video = tmp_path / "out_annotated.mp4"

    detections = [
        {
            "category": "drainage",
            "subtype": "choked_inlet",
            "start_sec": 0.0,
            "end_sec": 5.0,
            "box": [400, 100, 800, 600],
            "severity": 4,
            "confidence": 0.92,
        },
        {
            "category": "garbage",
            "subtype": "solid_waste_pile",
            "start_sec": 0.0,
            "end_sec": 5.0,
            "box": [200, 300, 600, 700],
            "severity": 3,
            "confidence": 0.86,
        }
    ]

    res = generate_annotated_surveillance_video(
        video_path=fixture_path,
        output_path=out_video,
        detections=detections,
        camera_meta={"name": "Test Cam", "id": "TEST-01"},
        drainage_score=85.0,
        garbage_score=78.0,
        water_depth_cm=20.0,
    )

    assert res.exists()
    assert res.stat().st_size > 1000

def test_temporal_telemetry():
    from app.core.evidence import get_temporal_telemetry
    # Initial phase (t = 0.5s of 10s)
    d1, g1, dep1, comp1, band1, status1 = get_temporal_telemetry(0.5, 10.0, 94.0, 90.0, 28.0)
    assert d1 >= 85.0
    assert g1 >= 80.0
    assert band1 == "CRITICAL"
    assert "CHOKED" in status1

    # Cleaned phase (t = 8.5s of 10s)
    d2, g2, dep2, comp2, band2, status2 = get_temporal_telemetry(8.5, 10.0, 94.0, 90.0, 28.0)
    assert d2 < 40.0
    assert g2 < 35.0
    assert band2 in ["OPTIMAL", "WATCH", "LOW"]
    assert "CLEANED" in status2


def test_compute_iou():
    from app.core.evidence import compute_iou
    box1 = [100, 100, 200, 200]
    box2 = [100, 100, 200, 200]
    assert compute_iou(box1, box2) == 1.0

    box3 = [300, 300, 400, 400]
    assert compute_iou(box1, box3) == 0.0

    box4 = [150, 100, 250, 200]
    iou = compute_iou(box1, box4)
    assert 0.3 < iou < 0.4


def test_parse_gemini_bbox():
    from app.core.evidence import parse_gemini_bbox
    # List [ymin, xmin, ymax, xmax] or [xmin, ymin, xmax, ymax]
    box = [200, 100, 600, 500]
    x1, y1, x2, y2 = parse_gemini_bbox(box, img_w=1000, img_h=500)
    assert x1 >= 0 and y1 >= 0
    assert x2 <= 1000 and y2 <= 500
    assert x2 > x1 and y2 > y1

    # Dict format
    box_dict = {"x_min": 150, "y_min": 250, "x_max": 450, "y_max": 750}
    x1, y1, x2, y2 = parse_gemini_bbox(box_dict, img_w=1000, img_h=1000)
    assert (x1, y1, x2, y2) == (150, 250, 450, 750)


def test_garbage_tracker_kalman_and_drop_handling():
    from app.core.evidence import GarbageObjectTracker

    tracker = GarbageObjectTracker(
        bbox=[100, 100, 200, 200],
        track_id=1,
        confidence=0.88,
        description="Plastic bottle lying on the road",
        max_age=10,
    )
    assert tracker.active is True
    assert tracker.status == "TRACKING"
    assert tracker.id == 1

    # 1. Prediction step
    p_box = tracker.predict(img_w=640, img_h=480)
    assert tracker.time_since_update == 1
    assert tracker.status == "TRACKING (PREDICTED)"

    # 2. Update step on matching detection
    tracker.update([105, 102, 205, 202], confidence=0.92, description="Plastic bottle")
    assert tracker.time_since_update == 0
    assert tracker.status == "TRACKING"
    assert tracker.confidence == 0.92

    # 3. Disappearance test: after max_age frames without update, tracker deactivates
    for _ in range(12):
        tracker.predict(img_w=640, img_h=480)
    assert tracker.active is False


def test_garbage_discrimination_and_jumping_prevention(tmp_path):
    from app.core.evidence import generate_annotated_surveillance_video
    fixture_path = Path("tests/fixtures/sample_cctv.mp4")
    out_video = tmp_path / "discrimination_test.mp4"

    # Only garbage should be tracked; drains and roads must NOT receive bounding boxes
    mixed_detections = [
        {
            "category": "drainage",  # MUST BE IGNORED
            "subtype": "open_storm_drain",
            "start_sec": 0.0,
            "end_sec": 4.0,
            "box": [100, 200, 400, 600],
            "confidence": 0.95,
        },
        {
            "category": "road",  # MUST BE IGNORED
            "subtype": "asphalt_pavement",
            "start_sec": 0.0,
            "end_sec": 4.0,
            "box": [500, 100, 800, 900],
            "confidence": 0.90,
        },
        {
            "category": "garbage",  # LOW CONFIDENCE (< 0.70) MUST BE IGNORED
            "subtype": "uncertain_shadow",
            "start_sec": 0.0,
            "end_sec": 4.0,
            "box": [50, 50, 100, 100],
            "confidence": 0.45,
        },
        {
            "category": "garbage",  # VALID CONFIDENT GARBAGE (>= 0.70)
            "subtype": "plastic_waste_heap",
            "start_sec": 0.0,
            "end_sec": 4.0,
            "box": [300, 250, 600, 550],
            "confidence": 0.89,
        },
    ]

    res = generate_annotated_surveillance_video(
        video_path=fixture_path,
        output_path=out_video,
        detections=mixed_detections,
        confidence_threshold=0.70,
    )
    assert res.exists()
    assert res.stat().st_size > 1000



