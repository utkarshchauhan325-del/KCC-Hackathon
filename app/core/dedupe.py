"""Deduplication engine for CivicEye incident sightings."""

from typing import List, Tuple
from app.core.schemas import InfraIssue, BBox
from app.core.evidence import timestamp_to_seconds

def compute_bbox_iou(box1: BBox, box2: BBox) -> float:
    """Compute Intersection over Union (IoU) between two normalized BBoxes (0-1000)."""
    inter_ymin = max(box1.ymin, box2.ymin)
    inter_xmin = max(box1.xmin, box2.xmin)
    inter_ymax = min(box1.ymax, box2.ymax)
    inter_xmax = min(box1.xmax, box2.xmax)

    inter_h = max(0, inter_ymax - inter_ymin)
    inter_w = max(0, inter_xmax - inter_xmin)
    inter_area = inter_h * inter_w

    area1 = max(0, box1.ymax - box1.ymin) * max(0, box1.xmax - box1.xmin)
    area2 = max(0, box2.ymax - box2.ymin) * max(0, box2.xmax - box2.xmin)
    union_area = area1 + area2 - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / float(union_area)

def deduplicate_infra_issues(
    issues: List[InfraIssue],
    time_window_sec: float = 10.0,
    iou_threshold: float = 0.40
) -> List[InfraIssue]:
    """Merge repeated sightings of the same civic issue within a time window having overlapping boxes.
    
    Keeps the sighting with the highest confidence.
    """
    if not issues:
        return []

    # Sort primarily by confidence descending so highest confidence is considered first
    sorted_issues = sorted(issues, key=lambda x: x.confidence, reverse=True)
    retained: List[InfraIssue] = []

    for candidate in sorted_issues:
        cand_ts = timestamp_to_seconds(candidate.best_frame_ts)
        is_duplicate = False

        for existing in retained:
            if existing.category == candidate.category and existing.subtype == candidate.subtype:
                exist_ts = timestamp_to_seconds(existing.best_frame_ts)
                time_diff = abs(exist_ts - cand_ts)
                if time_diff <= time_window_sec:
                    iou = compute_bbox_iou(existing.box, candidate.box)
                    if iou >= iou_threshold:
                        is_duplicate = True
                        break

        if not is_duplicate:
            retained.append(candidate)

    # Return issues sorted chronologically
    return sorted(retained, key=lambda x: timestamp_to_seconds(x.best_frame_ts))
