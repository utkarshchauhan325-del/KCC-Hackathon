import pytest
from pydantic import ValidationError
from app.core.schemas import (
    BBox,
    InfraIssue,
    InfraAnalysisResponse,
    ViolatorEvent,
    ViolatorAnalysisResponse,
    SewerAssessment,
)

def test_bbox_valid():
    box = BBox(ymin=0, xmin=10, ymax=900, xmax=1000)
    assert box.ymin == 0
    assert box.xmax == 1000

def test_bbox_out_of_bounds():
    with pytest.raises(ValidationError):
        BBox(ymin=-5, xmin=0, ymax=1000, xmax=1000)
    with pytest.raises(ValidationError):
        BBox(ymin=0, xmin=0, ymax=1001, xmax=1000)

def test_infra_issue_valid():
    issue = InfraIssue(
        category="garbage",
        subtype="dump_pile",
        severity=3,
        start_ts="00:15",
        end_ts="00:25",
        best_frame_ts="00:20",
        box=BBox(ymin=200, xmin=200, ymax=500, xmax=500),
        description="Large roadside garbage accumulation.",
        confidence=0.88,
    )
    assert issue.category == "garbage"
    assert issue.severity == 3

def test_infra_issue_invalid_severity():
    with pytest.raises(ValidationError):
        InfraIssue(
            category="garbage",
            subtype="dump_pile",
            severity=6,  # Valid range is 1-5
            start_ts="00:15",
            end_ts="00:25",
            best_frame_ts="00:20",
            box=BBox(ymin=200, xmin=200, ymax=500, xmax=500),
            description="Invalid severity test.",
            confidence=0.88,
        )

def test_violator_event_valid():
    event = ViolatorEvent(
        act_ts="01:10",
        best_frame_ts="01:12",
        person_box=BBox(ymin=100, xmin=100, ymax=400, xmax=300),
        garbage_box=BBox(ymin=350, xmin=280, ymax=420, xmax=340),
        vehicle_box=BBox(ymin=200, xmin=400, ymax=600, xmax=800),
        vehicle_type="auto-rickshaw",
        plate_text="DL 01 AB 1234",
        plate_box=BBox(ymin=500, xmin=550, ymax=540, xmax=650),
        plate_legibility="clear",
        description="Individual in blue shirt dumping bag from auto-rickshaw",
        confidence=0.85,
    )
    assert event.vehicle_type == "auto-rickshaw"
    assert event.plate_legibility == "clear"

def test_violator_response_container():
    resp = ViolatorAnalysisResponse(events=[])
    assert len(resp.events) == 0
