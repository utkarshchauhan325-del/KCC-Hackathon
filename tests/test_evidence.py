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

def test_generate_annotated_surveillance_video_without_detector(tmp_path):
    from app.core.evidence import generate_annotated_surveillance_video
    from app.core.schemas import InfraIssue

    issue = InfraIssue(
        category="drainage", subtype="blocked_drain", severity=4, start_ts="00:00", end_ts="00:03",
        best_frame_ts="00:01", box=BBox(ymin=400, xmin=100, ymax=800, xmax=600),
        description="Drain inlet covered with plastic.", confidence=0.9,
    )
    out_video = tmp_path / "out_annotated.mp4"
    res, summary = generate_annotated_surveillance_video(
        video_path=Path("tests/fixtures/sample_cctv.mp4"),
        output_path=out_video,
        vlm_issues=[issue],
        camera_meta={"name": "Test Cam", "id": "TEST-01"},
    )
    assert res.exists() and res.stat().st_size > 1000
    assert summary is None
