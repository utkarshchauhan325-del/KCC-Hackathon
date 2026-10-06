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


# --- CCTV Municipal Hazard Scoring Engine (Drainage, Garbage, Inundation) ---

DRAINAGE_WATER_LEVEL_WEIGHTS = {
    "none": 0.0,
    "damp": 0.20,
    "pooling": 0.50,
    "flowing_over": 0.85,
    "gushing": 1.0,
}

GARBAGE_INSIDE_WEIGHTS = {
    "none": 0.0,
    "light": 0.25,
    "moderate": 0.55,
    "heavy": 0.85,
    "fully_blocked": 1.0,
}

GARBAGE_NEAR_WEIGHTS = {
    "none": 0.0,
    "light": 0.25,
    "moderate": 0.60,
    "heavy": 1.0,
}

DUMP_VOLUME_WEIGHTS = {
    "none": 0.0,
    "light": 0.25,
    "moderate": 0.60,
    "heavy": 0.85,
    "massive": 1.0,
}

def compute_drainage_hazard_score(
    water_level: str = "pooling",
    grating_covered: bool = False,
    cover_missing_or_broken: bool = False,
    water_reaching_road: bool = False,
    wet_conditions: bool = False,
    conduit_depth_cm: Optional[float] = None,
) -> Tuple[float, str, Dict[str, Any]]:
    """Compute deterministic Drainage Hazard & Conduit Surcharge Risk Score (0-100).
    
    Formula weights:
      - Internal conduit water level: 35%
      - Grating / inlet blocked: 25%
      - Roadway overflow / surface spill: 20%
      - Structural hazard (broken/missing slab): 15%
      - Wet weather runoff factor: 5%
    
    Floor override: if water_level is 'flowing_over' or 'gushing', minimum floor is 70.
    """
    w_factor = DRAINAGE_WATER_LEVEL_WEIGHTS.get(water_level, 0.3)
    inlet_factor = 1.0 if grating_covered else 0.0
    road_spill_factor = 1.0 if water_reaching_road else 0.0
    structural_factor = 1.0 if cover_missing_or_broken else 0.0
    wet_factor = 1.0 if wet_conditions else 0.0

    # Depth adjustment if measured
    if conduit_depth_cm is not None and conduit_depth_cm > 0:
        depth_stress = min(1.0, conduit_depth_cm / 45.0)
        w_factor = max(w_factor, depth_stress)

    contrib_water = 35.0 * w_factor
    contrib_inlet = 25.0 * inlet_factor
    contrib_spill = 20.0 * road_spill_factor
    contrib_structural = 15.0 * structural_factor
    contrib_wet = 5.0 * wet_factor

    raw_score = contrib_water + contrib_inlet + contrib_spill + contrib_structural + contrib_wet
    is_floored = False
    final_score = raw_score

    if water_level in ["flowing_over", "gushing"] and raw_score < 70.0:
        final_score = 70.0
        is_floored = True

    final_score = max(0.0, min(100.0, round(final_score, 1)))
    band = get_risk_band(final_score)

    breakdown = {
        "score": final_score,
        "band": band,
        "is_floored": is_floored,
        "factors": {
            "water_level": {"val": water_level, "pts": round(contrib_water, 1)},
            "grating_covered": {"val": grating_covered, "pts": round(contrib_inlet, 1)},
            "water_reaching_road": {"val": water_reaching_road, "pts": round(contrib_spill, 1)},
            "cover_broken": {"val": cover_missing_or_broken, "pts": round(contrib_structural, 1)},
            "wet_conditions": {"val": wet_conditions, "pts": round(contrib_wet, 1)},
        }
    }
    return final_score, band, breakdown


def compute_garbage_hazard_score(
    trash_inside: str = "moderate",
    trash_near: str = "moderate",
    dumping_detected: bool = False,
    debris_volume: str = "moderate",
) -> Tuple[float, str, Dict[str, Any]]:
    """Compute deterministic Garbage & Debris Choking Score (0-100).
    
    Formula weights:
      - Trash inside conduit/inlet: 45%
      - Trash within 5m of intake mouth: 25%
      - Debris heap volume: 20%
      - Active illegal dumping activity: 10%
    
    Floor override: if trash_inside is 'fully_blocked', minimum floor is 75.
    """
    ti_factor = GARBAGE_INSIDE_WEIGHTS.get(trash_inside, 0.3)
    tn_factor = GARBAGE_NEAR_WEIGHTS.get(trash_near, 0.3)
    vol_factor = DUMP_VOLUME_WEIGHTS.get(debris_volume, 0.4)
    dump_factor = 1.0 if dumping_detected else 0.0

    contrib_inside = 45.0 * ti_factor
    contrib_near = 25.0 * tn_factor
    contrib_vol = 20.0 * vol_factor
    contrib_dump = 10.0 * dump_factor

    raw_score = contrib_inside + contrib_near + contrib_vol + contrib_dump
    is_floored = False
    final_score = raw_score

    if trash_inside == "fully_blocked" and raw_score < 75.0:
        final_score = 75.0
        is_floored = True

    final_score = max(0.0, min(100.0, round(final_score, 1)))
    band = get_risk_band(final_score)

    breakdown = {
        "score": final_score,
        "band": band,
        "is_floored": is_floored,
        "factors": {
            "trash_inside": {"val": trash_inside, "pts": round(contrib_inside, 1)},
            "trash_near": {"val": trash_near, "pts": round(contrib_near, 1)},
            "debris_volume": {"val": debris_volume, "pts": round(contrib_vol, 1)},
            "dumping_detected": {"val": dumping_detected, "pts": round(contrib_dump, 1)},
        }
    }
    return final_score, band, breakdown


def compute_cctv_composite_risk(
    drainage_score: float,
    garbage_score: float,
    water_depth_cm: float = 0.0,
) -> Tuple[float, str, Dict[str, Any]]:
    """Compute unified composite risk score (0-100) combining drainage, garbage, and depth."""
    depth_factor = min(100.0, (max(0.0, water_depth_cm) / 40.0) * 100.0)
    composite = (0.42 * drainage_score) + (0.38 * garbage_score) + (0.20 * depth_factor)
    composite = max(0.0, min(100.0, round(composite, 1)))

    if drainage_score >= 80.0 or garbage_score >= 80.0 or water_depth_cm >= 30.0 or composite >= 75.0:
        band = "Critical"
    elif composite >= 55.0 or drainage_score >= 60.0 or garbage_score >= 60.0:
        band = "High"
    elif composite >= 30.0:
        band = "Watch"
    else:
        band = "Low"

    breakdown = {
        "composite_score": composite,
        "band": band,
        "drainage_score": drainage_score,
        "garbage_score": garbage_score,
        "water_depth_cm": water_depth_cm,
        "depth_stress": round(depth_factor, 1),
    }
    return composite, band, breakdown



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

def rank_locations_by_all_attributes(
    locations: List[Dict[str, Any]],
    weather_rain_chance: int,
    weather_total_precip_mm: float,
    current_temp: float = 24.0,
    humidity: int = 75,
    traffic_map: Optional[Dict[str, Any]] = None,
    force_refresh_traffic: bool = False,
) -> List[Dict[str, Any]]:
    """Enrich and rank all municipal monitoring locations on the basis of ALL attributes:
    1. Precipitation intensity (mm) from WeatherAPI
    2. Traffic congestion and gridlock (%) from TomTom Traffic Flow API
    3. Conduit hydraulic saturation (water_level_pct)
    4. Debris obstruction index (blockage_pct)
    
    Also identifies which place is the #1 busiest corridor in Pune right now.
    """
    from app.core.traffic_client import fetch_bulk_traffic, _get_fallback_traffic

    if traffic_map is None:
        traffic_map = fetch_bulk_traffic(locations, force_refresh=force_refresh_traffic)

    enriched: List[Dict[str, Any]] = []
    seen_precips = set()

    # Step 1: Calculate precipitation and attach raw traffic
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
        
        p_val = metrics_preview["precip_mm"]
        while p_val in seen_precips:
            p_val = round(p_val + 0.1, 1)
        seen_precips.add(p_val)

        metrics = compute_location_weather_risk(
            loc=loc_copy,
            weather_rain_chance=weather_rain_chance,
            weather_total_precip_mm=weather_total_precip_mm,
            current_temp=current_temp,
            humidity=humidity,
            loc_index=idx,
            assigned_precip_mm=p_val
        )

        # Retrieve TomTom Traffic data
        loc_id = loc_copy.get("id", "")
        tf = traffic_map.get(loc_id)
        if tf is None:
            tf = _get_fallback_traffic(
                float(loc_copy.get("lat", 18.52)),
                float(loc_copy.get("lng", 73.85)),
                loc_id,
                float(loc_copy.get("water_level_pct", 0.0)),
                "Cache Miss"
            )

        # Dedicated 'traffic' attribute object requested by user
        traffic_delay = max(0, tf.current_travel_time_sec - tf.free_flow_travel_time_sec)
        loc_copy["traffic"] = {
            "congestion_pct": tf.congestion_pct,
            "traffic_level": tf.traffic_level,
            "current_speed_kmh": tf.current_speed_kmh,
            "free_flow_kmh": tf.free_flow_kmh,
            "delay_sec": traffic_delay,
            "road_closure": tf.road_closure,
            "is_busiest": False,
            "traffic_rank": 0,
            "is_live": tf.is_live,
            "last_updated": tf.last_updated,
            "source": "TomTom Traffic Flow API" if tf.is_live else "Model Baseline",
        }
        loc_copy["traffic_congestion_pct"] = tf.congestion_pct
        loc_copy["traffic_speed_kmh"] = tf.current_speed_kmh
        loc_copy["traffic_level"] = tf.traffic_level
        loc_copy["traffic_delay_sec"] = traffic_delay
        loc_copy["is_busiest_traffic"] = False

        loc_copy["precip_mm"] = metrics["precip_mm"]
        loc_copy["local_precip_load_mm"] = metrics["precip_mm"]
        loc_copy["rainfall_3h"] = int(round(metrics["precip_mm"]))
        loc_copy["rain_chance_pct"] = metrics["local_rain_chance"]
        loc_copy["flood_probability_pct"] = metrics["flood_probability_pct"]

        enriched.append(loc_copy)

    # Step 2: Identify and rank traffic across all places to find the MOST BUSIEST place
    # Primary traffic sort: congestion_pct desc, delay desc, current_speed asc
    traffic_sorted = sorted(
        enriched,
        key=lambda x: (
            x["traffic_congestion_pct"],
            x["traffic_delay_sec"],
            -x["traffic_speed_kmh"]
        ),
        reverse=True
    )
    for t_rank, t_loc in enumerate(traffic_sorted, 1):
        t_loc["traffic"]["traffic_rank"] = t_rank
        t_loc["traffic_rank"] = t_rank
        if t_rank == 1:
            t_loc["traffic"]["is_busiest"] = True
            t_loc["is_busiest_traffic"] = True
            t_loc["busiest_corridor_title"] = f"🚗 #1 Most Busiest Corridor: {t_loc['name']} ({t_loc['traffic_congestion_pct']}% Congestion | {t_loc['traffic_speed_kmh']} km/h)"

    # Step 3: Compute Multi-Attribute Composite Score based on ALL ATTRIBUTES
    # Weights:
    # 30% Precipitation Intensity (mm normalized to 36mm baseline)
    # 25% Traffic Congestion (TomTom gridlock %)
    # 25% Hydraulic Conduit Saturation (water_level_pct)
    # 20% Debris Blockage Obstruction (blockage_pct)
    for loc_item in enriched:
        p_stress = min(100.0, (loc_item["precip_mm"] / 36.0) * 100.0)
        t_jam = float(loc_item["traffic_congestion_pct"])
        w_sat = float(loc_item.get("water_level_pct", 50))
        b_choke = float(loc_item.get("blockage_pct", 50))

        contrib_p = 0.30 * p_stress
        contrib_t = 0.25 * t_jam
        contrib_w = 0.25 * w_sat
        contrib_b = 0.20 * b_choke

        comp_score = round(contrib_p + contrib_t + contrib_w + contrib_b, 1)
        comp_score = max(0.0, min(100.0, comp_score))

        loc_item["composite_score"] = comp_score
        loc_item["risk_score"] = int(round(comp_score))

        # Classify risk level based on multi-attribute stress and hydraulic thresholds
        is_stressed = (w_sat >= 78 and b_choke >= 60) or comp_score >= 65.0
        if is_stressed or comp_score >= 65.0 or w_sat >= 82:
            loc_item["risk_level"] = "Critical"
        elif comp_score >= 50.0 or w_sat >= 65:
            loc_item["risk_level"] = "High"
        elif comp_score >= 35.0:
            loc_item["risk_level"] = "Medium"
        else:
            loc_item["risk_level"] = "Low"

        loc_item["attribute_breakdown"] = {
            "precipitation_contrib": round(contrib_p, 1),
            "traffic_contrib": round(contrib_t, 1),
            "water_level_contrib": round(contrib_w, 1),
            "blockage_contrib": round(contrib_b, 1),
            "p_stress": round(p_stress, 1),
            "t_jam": int(t_jam),
            "w_sat": int(w_sat),
            "b_choke": int(b_choke),
        }

        # Multi-attribute status description
        if comp_score >= 70.0:
            loc_item["status"] = "Critical Gridlock & Flood"
        elif comp_score >= 55.0:
            loc_item["status"] = "Heavy Traffic Surcharge"
        elif comp_score >= 35.0:
            loc_item["status"] = "Moderate Inflow / Congestion"
        else:
            loc_item["status"] = "Optimal Flow & Clearway"

    # Step 4: Rank strictly on the basis of ALL ATTRIBUTES together
    enriched.sort(
        key=lambda x: (
            x["composite_score"],
            x["precip_mm"],
            x["traffic_congestion_pct"],
            x.get("water_level_pct", 0),
            x.get("blockage_pct", 0)
        ),
        reverse=True
    )

    # Assign priority rank and actionable multi-attribute directive
    for idx, item in enumerate(enriched, 1):
        item["priority_rank"] = idx
        t_info = f"🚗 Traffic: {item['traffic_congestion_pct']}% ({item['traffic_speed_kmh']} km/h)"
        p_info = f"🌧️ Precip: {item['precip_mm']} mm"
        w_info = f"💧 Conduit: {item['water_level_pct']}%"
        if idx <= 5:
            item["priority_directive"] = f"🚨 Rank #{idx} Emergency ({item['composite_score']}/100): {p_info} | {t_info} | {w_info} — Dispatch Quick Response"
        elif idx <= 15:
            item["priority_directive"] = f"⚠️ Rank #{idx} High Alert ({item['composite_score']}/100): {p_info} | {t_info} — Traffic Diversion & Jetting"
        elif idx <= 30:
            item["priority_directive"] = f"🟡 Rank #{idx} Watchlist ({item['composite_score']}/100): {p_info} | {t_info} — Telemetry Surveillance"
        else:
            item["priority_directive"] = f"🟢 Rank #{idx} Low Risk ({item['composite_score']}/100): {p_info} | {t_info} — Normal Operations"

    return enriched

def get_busiest_location(locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Identify and return the single most busiest location across Pune based on TomTom traffic."""
    busiest = next((l for l in locations if l.get("is_busiest_traffic")), None)
    if not busiest and locations:
        busiest = max(locations, key=lambda l: (l.get("traffic_congestion_pct", 0), l.get("traffic_delay_sec", 0)))
    return busiest or locations[0]

def rank_locations_by_flood_priority(
    locations: List[Dict[str, Any]],
    weather_rain_chance: int,
    weather_total_precip_mm: float,
    current_temp: float = 24.0,
    humidity: int = 75
) -> List[Dict[str, Any]]:
    """Enrich all locations and rank strictly by precipitation in mm descending."""
    enriched = rank_locations_by_all_attributes(
        locations=locations,
        weather_rain_chance=weather_rain_chance,
        weather_total_precip_mm=weather_total_precip_mm,
        current_temp=current_temp,
        humidity=humidity
    )
    # Sort strictly on the basis of precipitation (highest mm first)
    enriched.sort(key=lambda x: (x["precip_mm"], x["flood_probability_pct"], x["risk_score"]), reverse=True)

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



