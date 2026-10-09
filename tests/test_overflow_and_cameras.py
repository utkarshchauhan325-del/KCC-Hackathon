"""Tests for forecast-driven overflow projection and camera/dashboard score sync."""

from unittest import mock

from app.core import weather_client
from app.core.scoring import OVERFLOW_DANGER_PCT, compute_location_weather_risk, project_overflow
from app.ui import pune_data
from app.ui.pune_data import ASSIGNED_CAMERAS, PUNE_LOCATIONS, apply_camera_scores, location_for_job


def test_no_rain_forecast_means_no_rain_at_locations():
    loc = {"zone": "West", "drain_type": "RCC Pipe 600mm", "water_level_pct": 40, "blockage_pct": 30, "lat": 18.5, "lng": 73.8}
    dry = compute_location_weather_risk(loc, weather_rain_chance=5, weather_total_precip_mm=0.0)
    wet = compute_location_weather_risk(loc, weather_rain_chance=90, weather_total_precip_mm=40.0)
    assert dry["precip_mm"] == 0.0
    assert wet["precip_mm"] > 30.0
    assert wet["risk_score"] > dry["risk_score"]


def test_overflow_projection_rain_fills_and_dry_drains():
    dry = project_overflow(60, 40, "Stormwater Drain 900mm", [0.0] * 24)
    assert dry["overflow_eta_h"] is None
    assert dry["saturation_forecast"][-1] < 60

    storm = project_overflow(60, 40, "Stormwater Drain 900mm", [5.0] * 24)
    assert storm["overflow_eta_h"] is not None and storm["overflow_eta_h"] <= 3
    assert storm["projected_peak_pct"] >= OVERFLOW_DANGER_PCT

    already = project_overflow(90, 80, "Box Culvert 1200mm", [0.0] * 24)
    assert already["overflow_eta_h"] == 0


def test_blocked_drain_overflows_sooner():
    rain = [2.0] * 24
    clear = project_overflow(50, 0, "Stormwater Drain 900mm", rain)
    blocked = project_overflow(50, 90, "Stormwater Drain 900mm", rain)
    assert blocked["overflow_eta_h"] < clear["overflow_eta_h"]


def test_dashboard_uses_camera_scores():
    locations = [dict(l, composite_score=50.0, risk_score=50, precip_mm=0.0) for l in PUNE_LOCATIONS]
    ranked = apply_camera_scores(locations)
    by_id = {l["id"]: l for l in ranked}
    for cam in ASSIGNED_CAMERAS:
        loc = by_id[cam["location_id"]]
        assert loc["composite_score"] == cam["composite_score"]
        assert loc["blockage_pct"] == cam["blockage_index"]
        assert loc["cctv_camera"] == cam["id"]
    assert [l["priority_rank"] for l in ranked] == list(range(1, len(ranked) + 1))


def test_ranked_locations_carry_overflow_forecast():
    weather = weather_client._get_fallback_weather("test")
    with mock.patch.object(weather_client, "fetch_live_pune_weather", return_value=weather):
        locations = pune_data.get_all_attribute_ranked_locations()
    assert len(locations) == len(PUNE_LOCATIONS)
    assert all(len(l["saturation_forecast"]) == 24 for l in locations)
    assert all("overflow_outlook" in l for l in locations)


def test_location_for_job():
    cam = next(c for c in ASSIGNED_CAMERAS if c["video"])
    assert location_for_job(cam["video"], None)["id"] == cam["location_id"]
    swargate = next(l for l in PUNE_LOCATIONS if l["id"] == "LOC-03")
    assert location_for_job("other.mp4", f"{swargate['lat']}, {swargate['lng']}")["id"] == "LOC-03"
    assert location_for_job("other.mp4", "not gps")["id"] == PUNE_LOCATIONS[0]["id"]
