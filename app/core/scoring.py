"""Deterministic Sewer Overflow Risk Scoring Engine.

Computes a 0-100 score and risk band from categorical VLM observations.
"""

from typing import Tuple, Dict, Any
from app.config import settings
from app.core.schemas import SewerAssessment

# Categorical factor weight lookups
WATER_LEVEL_MAP = {
    "none": 0.0,
    "damp": 0.2,
    "pooling": 0.5,
    "flowing_over": 0.85,
    "gushing": 1.0,
}

TRASH_INSIDE_MAP = {
    "none": 0.0,
    "light": 0.25,
    "moderate": 0.55,
    "heavy": 0.85,
    "fully_blocked": 1.0,
}

TRASH_NEAR_MAP = {
    "none": 0.0,
    "light": 0.25,
    "moderate": 0.60,
    "heavy": 1.0,
}

def get_risk_band(score: float) -> str:
    """Classify score into operational risk band."""
    if score >= 80.0:
        return "Critical"
    elif score >= 60.0:
        return "High"
    elif score >= 30.0:
        return "Watch"
    else:
        return "Low"

def compute_sewer_score(assessment: SewerAssessment) -> Tuple[float, str, Dict[str, Any]]:
    """Compute deterministic sewer overflow score (0-100), risk band, and factor breakdown.
    
    Formula:
      score = 100 * ( 0.35 * water
                    + 0.25 * trash_inside
                    + 0.15 * trash_near
                    + 0.10 * inlet_blocked
                    + 0.10 * hazard
                    + 0.05 * wet_conditions )
    
    Override: if water_level is flowing_over or gushing, floor score at 70.
    """
    w_factor = WATER_LEVEL_MAP.get(assessment.water_level, 0.0)
    ti_factor = TRASH_INSIDE_MAP.get(assessment.trash_inside, 0.0)
    tn_factor = TRASH_NEAR_MAP.get(assessment.trash_near, 0.0)
    ib_factor = 1.0 if assessment.grating_covered else 0.0
    haz_factor = 1.0 if (assessment.cover_missing_or_broken or assessment.water_reaching_road) else 0.0
    wet_factor = 1.0 if assessment.wet_conditions else 0.0

    contrib_water = settings.WEIGHT_WATER * w_factor * 100
    contrib_trash_inside = settings.WEIGHT_TRASH_INSIDE * ti_factor * 100
    contrib_trash_near = settings.WEIGHT_TRASH_NEAR * tn_factor * 100
    contrib_inlet = settings.WEIGHT_INLET_BLOCKED * ib_factor * 100
    contrib_hazard = settings.WEIGHT_HAZARD * haz_factor * 100
    contrib_wet = settings.WEIGHT_WET_CONDITIONS * wet_factor * 100

    raw_score = (
        contrib_water
        + contrib_trash_inside
        + contrib_trash_near
        + contrib_inlet
        + contrib_hazard
        + contrib_wet
    )

    is_floored = False
    final_score = raw_score
    if assessment.water_level in ["flowing_over", "gushing"] and raw_score < settings.SEWER_OVERFLOW_FLOOR:
        final_score = settings.SEWER_OVERFLOW_FLOOR
        is_floored = True

    # Clamp to [0, 100]
    final_score = max(0.0, min(100.0, round(final_score, 1)))
    band = get_risk_band(final_score)

    breakdown = {
        "raw_score": round(raw_score, 1),
        "final_score": final_score,
        "band": band,
        "is_floored": is_floored,
        "factors": {
            "water": {"value": assessment.water_level, "contribution": round(contrib_water, 2)},
            "trash_inside": {"value": assessment.trash_inside, "contribution": round(contrib_trash_inside, 2)},
            "trash_near": {"value": assessment.trash_near, "contribution": round(contrib_trash_near, 2)},
            "inlet_blocked": {"value": assessment.grating_covered, "contribution": round(contrib_inlet, 2)},
            "hazard": {"value": haz_factor > 0, "contribution": round(contrib_hazard, 2)},
            "wet_conditions": {"value": assessment.wet_conditions, "contribution": round(contrib_wet, 2)},
        }
    }

    return final_score, band, breakdown
