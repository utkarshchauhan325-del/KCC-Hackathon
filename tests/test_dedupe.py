import pytest
from app.core.schemas import InfraIssue, BBox
from app.core.dedupe import compute_bbox_iou, deduplicate_infra_issues

def test_iou_identical_boxes():
    b1 = BBox(ymin=100, xmin=100, ymax=200, xmax=200)
    b2 = BBox(ymin=100, xmin=100, ymax=200, xmax=200)
    assert compute_bbox_iou(b1, b2) == 1.0

def test_iou_disjoint_boxes():
    b1 = BBox(ymin=0, xmin=0, ymax=50, xmax=50)
    b2 = BBox(ymin=100, xmin=100, ymax=200, xmax=200)
    assert compute_bbox_iou(b1, b2) == 0.0

def test_deduplicate_merges_overlapping_sightings():
    sighting1 = InfraIssue(
        category="garbage",
        subtype="dump_pile",
        severity=3,
        start_ts="00:02",
        end_ts="00:06",
        best_frame_ts="00:04",
        box=BBox(ymin=200, xmin=200, ymax=400, xmax=400),
        description="Garbage dump first sighting",
        confidence=0.75,
    )
    sighting2 = InfraIssue(
        category="garbage",
        subtype="dump_pile",
        severity=3,
        start_ts="00:04",
        end_ts="00:08",
        best_frame_ts="00:06",
        box=BBox(ymin=210, xmin=205, ymax=405, xmax=410), # High overlap
        description="Garbage dump clearer view",
        confidence=0.92, # Higher confidence
    )
    different_issue = InfraIssue(
        category="drainage",
        subtype="open_manhole",
        severity=5,
        start_ts="00:05",
        end_ts="00:08",
        best_frame_ts="00:06",
        box=BBox(ymin=600, xmin=600, ymax=800, xmax=800),
        description="Open drain",
        confidence=0.85,
    )

    deduped = deduplicate_infra_issues([sighting1, sighting2, different_issue])
    assert len(deduped) == 2
    # Check that the higher confidence garbage sighting was retained
    garbage_issue = next(i for i in deduped if i.category == "garbage")
    assert garbage_issue.confidence == 0.92
    assert garbage_issue.description == "Garbage dump clearer view"
