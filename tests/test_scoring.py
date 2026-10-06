import pytest
from app.core.schemas import SewerAssessment
from app.core.scoring import compute_sewer_score

def test_scoring_dry_clean():
    """Case 1: Perfectly clean, dry drain -> Score 0, Low."""
    assessment = SewerAssessment(
        water_level="none",
        water_reaching_road=False,
        trash_inside="none",
        trash_near="none",
        grating_covered=False,
        cover_missing_or_broken=False,
        wet_conditions=False,
        hazards=[],
        confidence=0.95
    )
    score, band, breakdown = compute_sewer_score(assessment)
    assert score == 0.0
    assert band == "Low"
    assert breakdown["is_floored"] is False

def test_scoring_worst_case_catastrophic():
    """Case 2: Gushing, fully blocked, heavy trash, covered grating, road flooded -> Score 100, Critical."""
    assessment = SewerAssessment(
        water_level="gushing",
        water_reaching_road=True,
        trash_inside="fully_blocked",
        trash_near="heavy",
        grating_covered=True,
        cover_missing_or_broken=True,
        wet_conditions=True,
        hazards=["open hole", "traffic hazard"],
        confidence=0.99
    )
    score, band, breakdown = compute_sewer_score(assessment)
    assert score == 100.0
    assert band == "Critical"

def test_scoring_flowing_over_override_floor():
    """Case 3: Flowing over but clean drain -> Floor at 70 override."""
    assessment = SewerAssessment(
        water_level="flowing_over", # 0.35 * 0.85 * 100 = 29.75
        water_reaching_road=False,
        trash_inside="none",
        trash_near="none",
        grating_covered=False,
        cover_missing_or_broken=False,
        wet_conditions=False,
        hazards=[],
        confidence=0.90
    )
    score, band, breakdown = compute_sewer_score(assessment)
    # raw score ~29.75, but flowing_over triggers floor 70
    assert score == 70.0
    assert band == "High"
    assert breakdown["is_floored"] is True

def test_scoring_gushing_override_floor():
    """Case 4: Gushing with no trash -> Floor at 70 override."""
    assessment = SewerAssessment(
        water_level="gushing", # 0.35 * 1.0 * 100 = 35.0
        water_reaching_road=False,
        trash_inside="none",
        trash_near="none",
        grating_covered=False,
        cover_missing_or_broken=False,
        wet_conditions=False,
        hazards=[],
        confidence=0.90
    )
    score, band, breakdown = compute_sewer_score(assessment)
    assert score == 70.0
    assert band == "High"
    assert breakdown["is_floored"] is True

def test_scoring_damp_with_light_trash():
    """Case 5: Damp with light trash -> Low band."""
    assessment = SewerAssessment(
        water_level="damp", # 0.35 * 0.2 * 100 = 7.0
        water_reaching_road=False,
        trash_inside="light", # 0.25 * 0.25 * 100 = 6.25
        trash_near="light", # 0.15 * 0.25 * 100 = 3.75
        grating_covered=False,
        cover_missing_or_broken=False,
        wet_conditions=False,
        hazards=[],
        confidence=0.85
    )
    score, band, breakdown = compute_sewer_score(assessment)
    # raw score = 7.0 + 6.25 + 3.75 = 17.0
    assert score == 17.0
    assert band == "Low"

def test_scoring_pooling_water_and_moderate_trash():
    """Case 6: Pooling water + moderate trash + wet conditions -> Watch band (30-59)."""
    assessment = SewerAssessment(
        water_level="pooling", # 0.35 * 0.5 * 100 = 17.5
        water_reaching_road=False,
        trash_inside="moderate", # 0.25 * 0.55 * 100 = 13.75
        trash_near="moderate", # 0.15 * 0.6 * 100 = 9.0
        grating_covered=False,
        cover_missing_or_broken=False,
        wet_conditions=True, # 0.05 * 1.0 * 100 = 5.0
        hazards=[],
        confidence=0.90
    )
    score, band, breakdown = compute_sewer_score(assessment)
    # 17.5 + 13.75 + 9.0 + 5.0 = 45.25 -> rounded to 45.3
    assert 40.0 <= score <= 50.0
    assert band == "Watch"

def test_scoring_heavy_trash_blocked_inlet_broken_cover():
    """Case 7: Heavy trash, covered grating, broken cover -> High band without water override."""
    assessment = SewerAssessment(
        water_level="pooling", # 17.5
        water_reaching_road=False,
        trash_inside="heavy", # 0.25 * 0.85 * 100 = 21.25
        trash_near="heavy", # 0.15 * 1.0 * 100 = 15.0
        grating_covered=True, # 10.0
        cover_missing_or_broken=True, # 10.0 (hazard)
        wet_conditions=False,
        hazards=["missing slab"],
        confidence=0.88
    )
    score, band, breakdown = compute_sewer_score(assessment)
    # 17.5 + 21.25 + 15.0 + 10.0 + 10.0 = 73.75 -> 73.8
    assert 70.0 <= score <= 75.0
    assert band == "High"
    assert breakdown["is_floored"] is False

def test_scoring_water_reaching_road_triggers_hazard():
    """Case 8: Water reaching road counts as hazard factor."""
    assessment = SewerAssessment(
        water_level="none",
        water_reaching_road=True, # hazard = 10.0
        trash_inside="none",
        trash_near="none",
        grating_covered=False,
        cover_missing_or_broken=False,
        wet_conditions=False,
        hazards=[],
        confidence=0.90
    )
    score, band, breakdown = compute_sewer_score(assessment)
    assert score == 10.0
    assert breakdown["factors"]["hazard"]["value"] is True

def test_drainage_hazard_scoring():
    from app.core.scoring import compute_drainage_hazard_score
    # Clean dry conduit
    score_clean, band_clean, _ = compute_drainage_hazard_score(
        water_level="none",
        grating_covered=False,
        cover_missing_or_broken=False,
        water_reaching_road=False,
        wet_conditions=False,
    )
    assert score_clean == 0.0
    assert band_clean == "Low"

    # Severe surcharge with choked inlet & road spill
    score_crit, band_crit, b_crit = compute_drainage_hazard_score(
        water_level="gushing",
        grating_covered=True,
        cover_missing_or_broken=True,
        water_reaching_road=True,
        wet_conditions=True,
        conduit_depth_cm=35.0,
    )
    assert score_crit >= 80.0
    assert band_crit == "Critical"
    assert b_crit["score"] == score_crit

def test_garbage_hazard_scoring():
    from app.core.scoring import compute_garbage_hazard_score
    # Clean drain
    score_clean, band_clean, _ = compute_garbage_hazard_score(
        trash_inside="none",
        trash_near="none",
        dumping_detected=False,
        debris_volume="none",
    )
    assert score_clean == 0.0
    assert band_clean == "Low"

    # Fully blocked with heavy debris & dumping
    score_block, band_block, _ = compute_garbage_hazard_score(
        trash_inside="fully_blocked",
        trash_near="heavy",
        dumping_detected=True,
        debris_volume="massive",
    )
    assert score_block >= 75.0
    assert band_block in ["High", "Critical"]

def test_cctv_composite_risk():
    from app.core.scoring import compute_cctv_composite_risk
    comp_score, comp_band, breakdown = compute_cctv_composite_risk(
        drainage_score=94.0,
        garbage_score=90.0,
        water_depth_cm=28.0,
    )
    assert comp_score >= 80.0
    assert comp_band == "Critical"
    assert breakdown["depth_stress"] == 70.0

