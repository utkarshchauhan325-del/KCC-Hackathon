"""Unit tests for WeatherAPI client and deterministic flood priority scoring engine."""

import pytest
from app.core.weather_client import fetch_live_pune_weather, PuneWeatherData
from app.core.scoring import (
    compute_location_weather_risk,
    rank_locations_by_flood_priority,
    ZONE_OROGRAPHIC_FACTORS
)
from app.ui.pune_data import PUNE_LOCATIONS, get_weather_adjusted_locations, get_live_pune_kpis

def test_weather_client_fetch():
    """Verify WeatherAPI client returns valid meteorological dataset."""
    weather = fetch_live_pune_weather()
    assert isinstance(weather, PuneWeatherData)
    assert weather.location_name == "Pune"
    assert weather.temp_c > -10.0 and weather.temp_c < 55.0
    assert 0 <= weather.humidity <= 100
    assert 0 <= weather.daily_chance_of_rain <= 100
    assert len(weather.hourly_forecast) == 24

def test_deterministic_location_weather_risk():
    """Verify formula outputs valid clamped scores and flood probabilities."""
    sample_loc = {
        "id": "LOC-TEST",
        "name": "Test Culvert",
        "zone": "Central",
        "drain_type": "Box Culvert 1200mm",
        "water_level_pct": 85,
        "blockage_pct": 75,
    }

    metrics = compute_location_weather_risk(
        loc=sample_loc,
        weather_rain_chance=50,
        weather_total_precip_mm=5.0,
        current_temp=22.0,
        humidity=80
    )

    assert 0 <= metrics["risk_score"] <= 100
    assert 5 <= metrics["flood_probability_pct"] <= 99
    assert metrics["risk_level"] in ["Critical", "High", "Medium", "Low"]
    assert metrics["local_rain_chance"] >= 50  # Central zone has > 1.0 factor

def test_conduit_surcharge_effect():
    """Verify high blockage and narrow conduit increases flood probability."""
    loc_open = {
        "zone": "Central",
        "drain_type": "Open Trapezoidal Nullah",
        "water_level_pct": 40,
        "blockage_pct": 20,
    }
    loc_choked_culvert = {
        "zone": "Central",
        "drain_type": "Underpass Box Conduit",
        "water_level_pct": 90,
        "blockage_pct": 85,
    }

    low_res = compute_location_weather_risk(loc_open, 30, 1.0)
    high_res = compute_location_weather_risk(loc_choked_culvert, 30, 1.0)

    assert high_res["flood_probability_pct"] > low_res["flood_probability_pct"]
    assert high_res["risk_score"] > low_res["risk_score"]
    assert high_res["risk_level"] == "Critical"

def test_rank_locations_by_flood_priority():
    """Verify all 53 municipal locations receive distinct precipitation and are ordered by precipitation."""
    ranked = rank_locations_by_flood_priority(
        locations=PUNE_LOCATIONS,
        weather_rain_chance=45,
        weather_total_precip_mm=2.5,
        current_temp=24.0,
        humidity=75
    )

    assert len(ranked) == len(PUNE_LOCATIONS)
    
    # 1. Verify every single place has a DIFFERENT amount of precipitation in mm
    precip_values = [item["precip_mm"] for item in ranked]
    assert len(set(precip_values)) == len(PUNE_LOCATIONS)

    # 2. Verify rankings are strictly ordered on the basis of precipitation (highest mm first)
    for i in range(len(ranked) - 1):
        assert ranked[i]["precip_mm"] >= ranked[i + 1]["precip_mm"]

    # 3. Check 1-based sequential rank and priority directives
    for idx, item in enumerate(ranked, 1):
        assert item["priority_rank"] == idx
        assert "priority_directive" in item
        assert "flood_probability_pct" in item
        assert str(item["precip_mm"]) in item["priority_directive"]

def test_live_pune_kpis_calculation():
    """Verify dynamic KPIs compute correct sums from active locations."""
    locations = get_weather_adjusted_locations()
    kpis = get_live_pune_kpis(locations)

    assert kpis["critical_locations"] >= 1
    assert kpis["high_risk_locations"] >= 1
    assert kpis["drainage_risk"] >= 1
    assert "critical_diff" in kpis
