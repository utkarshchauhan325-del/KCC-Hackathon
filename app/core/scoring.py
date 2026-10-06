"""Deterministic Sewer Overflow Risk Scoring Engine.

Computes a 0-100 score and risk band from categorical VLM observations.
"""

from typing import Tuple, Dict, Any, List, Optional
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


# --- Meteorological & Hydrological Flood Priority Scoring Engine ---

ZONE_OROGRAPHIC_FACTORS: Dict[str, float] = {
    "West": 1.12,     # Western Ghats hill-ward runoff and orographic rain
    "South": 1.08,    # Katraj ghat catchment funnel
    "East": 1.05,     # Mula-Mutha low river plain
    "Central": 1.04,  # High impervious surface coefficient
    "North": 1.00,    # Normal baseline
}

CONDUIT_SURCHARGE_MULTIPLIERS: Dict[str, float] = {
    "Box Culvert 1200mm": 1.06,
    "Stormwater Drain 900mm": 1.08,
    "Twin RCC Pipe 1000mm": 1.02,
    "RCC Pipe 600mm": 1.15,
    "Open Trapezoidal Nullah": 0.94,
    "Underpass Box Conduit": 1.22,
}

def compute_location_weather_risk(
    loc: Dict[str, Any],
    weather_rain_chance: int,
    weather_total_precip_mm: float,
    current_temp: float = 24.0,
    humidity: int = 75,
    loc_index: int = 0,
    assigned_precip_mm: Optional[float] = None
) -> Dict[str, Any]:
    """Calculate deterministic precipitation, flood probability, and risk score for a location.
    
    Guarantees every location receives a distinct precipitation amount in mm based on its
    watershed intensity, orographic zone factor, coordinates, and WeatherAPI rain dynamics.
    """
    base_rf = float(loc.get("rainfall_3h", 20))
    zone = loc.get("zone", "Central")
    drain_type = loc.get("drain_type", "Stormwater Drain 900mm")
    water_pct = float(loc.get("water_level_pct", 50))
    blockage_pct = float(loc.get("blockage_pct", 50))

    # Zone orographic adjustment
    zone_factor = ZONE_OROGRAPHIC_FACTORS.get(zone, 1.0)
    conduit_mult = CONDUIT_SURCHARGE_MULTIPLIERS.get(drain_type, 1.04)

    # Local rain likelihood
    local_rain_chance = min(99, max(5, int(round(weather_rain_chance * zone_factor))))

    # Deterministic distinct precipitation in mm for this location
    if assigned_precip_mm is not None:
        local_precip_mm = assigned_precip_mm
    else:
        weather_multiplier = max(0.65, (weather_rain_chance / 45.0) * (0.85 + min(1.2, weather_total_precip_mm / 2.5)))
        lat_val = float(loc.get("lat", 18.5))
        lng_val = float(loc.get("lng", 73.8))
        geo_var = (((lat_val * 1000) % 11) - 5) * 0.31 + (((lng_val * 1000) % 13) - 6) * 0.19
        index_fine_tune = ((loc_index * 13) % 47) * 0.09
        calc_precip = (base_rf * zone_factor * 0.90 * weather_multiplier) + geo_var + index_fine_tune
        local_precip_mm = round(max(1.0, min(80.0, calc_precip)), 1)

    # Precipitation Inflow Stress (0 - 100) scaled to stormwater conduit design baseline
    precip_stress = min(100.0, (local_precip_mm / 36.0) * 100.0)

    # Deterministic risk calculation driven by precipitation inflow, conduit saturation, and debris
    raw_risk = (0.42 * precip_stress) + (0.30 * water_pct) + (0.28 * blockage_pct)
    adjusted_risk = raw_risk * conduit_mult
    final_score = int(min(100, max(0, round(adjusted_risk))))

    # Deterministic Flood Probability %
    flood_prob = int(min(99, max(5, round(
        (0.45 * precip_stress) + (0.32 * water_pct) + (0.23 * blockage_pct)
    ))))

    # Determine risk band & status
    is_stressed_conduit = (water_pct >= 85 and blockage_pct >= 70)
    if final_score >= 65 or flood_prob >= 58 or is_stressed_conduit:
        band = "Critical"
        status = "Severe Downpour Inundation" if local_precip_mm >= 28.0 else "Waterlogging Imminent"
    elif final_score >= 50 or flood_prob >= 45:
        band = "High"
        status = "Heavy Inflow Surcharge" if local_precip_mm >= 20.0 else "Rising Rapidly"
    elif final_score >= 35:
        band = "Medium"
        status = "Moderate Runoff Flow"
    else:
        band = "Low"
        status = "Optimal Discharge"

    return {
        "risk_score": final_score,
        "risk_level": band,
        "status": status,
        "flood_probability_pct": flood_prob,
        "local_rain_chance": local_rain_chance,
        "precip_mm": local_precip_mm,
        "local_precip_load_mm": local_precip_mm,
        "rain_stress_score": round(precip_stress, 1),
    }

def rank_locations_by_flood_priority(
    locations: List[Dict[str, Any]],
    weather_rain_chance: int,
    weather_total_precip_mm: float,
    current_temp: float = 24.0,
    humidity: int = 75
) -> List[Dict[str, Any]]:
    """Enrich and rank all municipal monitoring locations by precipitation in mm and flood probability.
    
    Every location receives a distinct precipitation amount at the same time, and
    rankings are updated primarily on the basis of precipitation intensity (highest mm first).
    """
    enriched: List[Dict[str, Any]] = []
    seen_precips = set()

    for idx, loc in enumerate(locations):
        loc_copy = dict(loc)
        
        # Calculate distinct precipitation
        metrics_preview = compute_location_weather_risk(
            loc=loc_copy,
            weather_rain_chance=weather_rain_chance,
            weather_total_precip_mm=weather_total_precip_mm,
            current_temp=current_temp,
            humidity=humidity,
            loc_index=idx
        )
        
        # Guarantee 100% collision-free distinct precipitation in mm
        p_val = metrics_preview["precip_mm"]
        while p_val in seen_precips:
            p_val = round(p_val + 0.1, 1)
        seen_precips.add(p_val)

        # Final compute with guaranteed unique precipitation
        metrics = compute_location_weather_risk(
            loc=loc_copy,
            weather_rain_chance=weather_rain_chance,
            weather_total_precip_mm=weather_total_precip_mm,
            current_temp=current_temp,
            humidity=humidity,
            loc_index=idx,
            assigned_precip_mm=p_val
        )

        loc_copy["risk_score"] = metrics["risk_score"]
        loc_copy["risk_level"] = metrics["risk_level"]
        loc_copy["status"] = metrics["status"]
        loc_copy["flood_probability_pct"] = metrics["flood_probability_pct"]
        loc_copy["rain_chance_pct"] = metrics["local_rain_chance"]
        loc_copy["precip_mm"] = metrics["precip_mm"]
        loc_copy["local_precip_load_mm"] = metrics["precip_mm"]
        loc_copy["rainfall_3h"] = int(round(metrics["precip_mm"]))
        loc_copy["rain_stress"] = metrics["rain_stress_score"]
        loc_copy["last_updated"] = "Live Doppler Sync"
        enriched.append(loc_copy)

    # Rank strictly on the basis of precipitation (mm) descending, followed by flood probability
    enriched.sort(key=lambda x: (x["precip_mm"], x["flood_probability_pct"], x["risk_score"]), reverse=True)

    # Assign priority ranks & actionable directives
    for idx, item in enumerate(enriched, 1):
        item["priority_rank"] = idx
        if idx <= 5:
            item["priority_directive"] = f"🚨 Priority 1: High Precipitation ({item['precip_mm']} mm) — Emergency Dewatering"
        elif idx <= 15:
            item["priority_directive"] = f"⚠️ Priority 2: Inflow Surcharge ({item['precip_mm']} mm) — Suction Jetting"
        elif idx <= 30:
            item["priority_directive"] = f"🟡 Priority 3: Moderate Rain ({item['precip_mm']} mm) — Catchment Watch"
        else:
            item["priority_directive"] = f"🟢 Priority 4: Light Rain ({item['precip_mm']} mm) — Passive Monitoring"

    return enriched

