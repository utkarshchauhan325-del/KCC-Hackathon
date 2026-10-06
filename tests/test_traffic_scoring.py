"""Unit tests for TomTom Traffic Intelligence & Multi-Attribute Ranking."""

import pytest
from app.core.traffic_client import (
    TrafficFlowData,
    fetch_point_traffic_flow,
    fetch_bulk_traffic,
    _get_fallback_traffic
)
from app.core.scoring import (
    rank_locations_by_all_attributes,
    get_busiest_location,
    rank_locations_by_flood_priority
)
from app.ui.pune_data import PUNE_LOCATIONS, get_busiest_traffic_corridor

def test_traffic_flow_schema():
    """Verify TrafficFlowData Pydantic model defaults and types."""
    data = TrafficFlowData(
        location_id="TEST-01",
        current_speed_kmh=18.5,
        free_flow_kmh=40.0,
        current_travel_time_sec=450,
        free_flow_travel_time_sec=240,
        congestion_pct=65,
        traffic_level="Heavy Congestion",
        is_live=True
    )
    assert data.location_id == "TEST-01"
    assert data.congestion_pct == 65
    assert data.traffic_level == "Heavy Congestion"
    assert data.is_live is True

def test_point_traffic_flow_fetch():
    """Verify live/fallback traffic fetch returns valid metrics for Pune coordinates."""
    # Pune coordinates (FC Road)
    tf = fetch_point_traffic_flow(lat=18.5255, lng=73.8415, location_id="LOC-02", water_level_pct=80.0)
    assert isinstance(tf, TrafficFlowData)
    assert tf.location_id == "LOC-02"
    assert 0 <= tf.congestion_pct <= 100
    assert tf.current_speed_kmh > 0
    assert tf.free_flow_kmh >= tf.current_speed_kmh or tf.traffic_level != ""

def test_fallback_traffic_deterministic():
    """Ensure deterministic fallback when API is unreachable or key is mock."""
    fb1 = _get_fallback_traffic(18.5186, 73.8785, "LOC-01", water_level_pct=90.0, reason="test")
    fb2 = _get_fallback_traffic(18.5186, 73.8785, "LOC-01", water_level_pct=90.0, reason="test")
    assert fb1.congestion_pct == fb2.congestion_pct
    assert fb1.current_speed_kmh == fb2.current_speed_kmh
    # Water level 90% should cause high congestion
    assert fb1.congestion_pct >= 60

def test_all_locations_have_traffic_attribute():
    """Verify EVERY location receives the 'traffic' attribute object and top-level helpers."""
    sample_locs = PUNE_LOCATIONS[:10]
    ranked = rank_locations_by_all_attributes(
        locations=sample_locs,
        weather_rain_chance=80,
        weather_total_precip_mm=35.0
    )
    assert len(ranked) == 10
    for loc in ranked:
        assert "traffic" in loc
        traffic_obj = loc["traffic"]
        assert isinstance(traffic_obj, dict)
        assert "congestion_pct" in traffic_obj
        assert "traffic_level" in traffic_obj
        assert "current_speed_kmh" in traffic_obj
        assert "free_flow_kmh" in traffic_obj
        assert "delay_sec" in traffic_obj
        assert "is_busiest" in traffic_obj
        assert "traffic_rank" in traffic_obj
        
        # Top-level convenience keys
        assert "traffic_congestion_pct" in loc
        assert "traffic_speed_kmh" in loc
        assert "traffic_level" in loc
        assert "is_busiest_traffic" in loc
        assert "composite_score" in loc
        assert "attribute_breakdown" in loc

def test_identify_most_busiest_place():
    """Verify the single most busiest traffic corridor is identified and tagged."""
    mock_locs = [
        {"id": "L1", "name": "Quiet Street", "lat": 18.50, "lng": 73.80, "water_level_pct": 20, "blockage_pct": 10},
        {"id": "L2", "name": "Busy Flyover", "lat": 18.52, "lng": 73.84, "water_level_pct": 95, "blockage_pct": 80},
        {"id": "L3", "name": "Mid Avenue", "lat": 18.53, "lng": 73.86, "water_level_pct": 50, "blockage_pct": 40},
    ]
    ranked = rank_locations_by_all_attributes(
        locations=mock_locs,
        weather_rain_chance=70,
        weather_total_precip_mm=25.0
    )
    busiest = get_busiest_location(ranked)
    assert busiest is not None
    assert busiest["is_busiest_traffic"] is True
    assert busiest["traffic"]["is_busiest"] is True
    assert busiest["traffic_rank"] == 1
    # Busiest should have the highest congestion
    for other in ranked:
        if other["id"] != busiest["id"]:
            assert busiest["traffic_congestion_pct"] >= other["traffic_congestion_pct"]

def test_multi_attribute_ranking():
    """Verify that ranking is computed on the basis of ALL attributes."""
    mock_locs = [
        {"id": "L1", "name": "Low Stress", "lat": 18.51, "lng": 73.81, "rainfall_3h": 10, "water_level_pct": 20, "blockage_pct": 15},
        {"id": "L2", "name": "Severe Crisis", "lat": 18.52, "lng": 73.85, "rainfall_3h": 40, "water_level_pct": 90, "blockage_pct": 85},
    ]
    ranked = rank_locations_by_all_attributes(
        locations=mock_locs,
        weather_rain_chance=90,
        weather_total_precip_mm=50.0
    )
    top = ranked[0]
    assert top["id"] == "L2"
    assert top["priority_rank"] == 1
    assert top["composite_score"] > ranked[1]["composite_score"]

    # Verify attribute breakdown contains all 4 components
    bd = top["attribute_breakdown"]
    assert "precipitation_contrib" in bd
    assert "traffic_contrib" in bd
    assert "water_level_contrib" in bd
    assert "blockage_contrib" in bd
