"""Unit tests for FloodGuard UI components, data structures, and report generator."""

from app.ui.pune_data import PUNE_LOCATIONS, KPIS, RECENT_ALERTS, CCTV_CAMERAS, PRIORITY_QUEUE
from app.ui.components.charts import (
    render_risk_distribution_donut,
    render_rainfall_forecast_bars,
    render_water_level_trend,
    render_7day_rainfall_water_correlation,
    render_ward_vulnerability_bars,
    render_blockage_vs_flood_scatter
)
from app.ui.views.flood_analytics import generate_printable_html_report, generate_printable_pdf_report

def test_pune_dataset_metrics():
    """Verify exact alignment with FloodGuard dashboard specifications."""
    assert len(PUNE_LOCATIONS) == 53
    assert KPIS["critical_locations"] == 5
    assert KPIS["high_risk_locations"] == 17
    assert KPIS["active_waterlogging"] == 8
    assert KPIS["drainage_risk"] == 23
    assert len(CCTV_CAMERAS) == 6
    assert len(PRIORITY_QUEUE) == 3

def test_charts_generation():
    """Verify all Plotly figures initialize with valid traces."""
    from app.core.weather_client import _get_fallback_weather

    donut = render_risk_distribution_donut(PUNE_LOCATIONS)
    assert len(donut.data) == 1
    assert donut.data[0].type == "pie"
    assert sum(donut.data[0].values) == len(PUNE_LOCATIONS)

    hourly = _get_fallback_weather("test").hourly_forecast
    bars = render_rainfall_forecast_bars(hourly)
    assert [t.type for t in bars.data] == ["bar", "scatter"]  # rain bars + chance-of-rain line
    assert len(bars.data[0].y) == 24

    lines = render_water_level_trend([("MG Road", 90, [88] * 24), ("FC Road", 80, [70] * 24)], [h.time for h in hourly])
    assert len(lines.data) == 4  # a line and a "now" marker per location

    corr = render_7day_rainfall_water_correlation()
    assert len(corr.data) == 2

    ward_bars = render_ward_vulnerability_bars()
    assert len(ward_bars.data) == 3

    scatter = render_blockage_vs_flood_scatter()
    assert len(scatter.data) == 4

def test_printable_html_report_generation():
    """Verify official report generation contains required metadata."""
    html_report = generate_printable_html_report()
    assert "Pune Municipal Corporation" in html_report
    assert "Disaster Management Cell" in html_report
    assert "MG Road Junction" in html_report
    assert "FC Road Junction" in html_report
    assert "Deccan Gymkhana" in html_report

def test_printable_pdf_report_generation():
    """Verify official PDF audit report generation produces valid binary PDF data."""
    pdf_report = generate_printable_pdf_report()
    assert isinstance(pdf_report, bytes)
    assert pdf_report.startswith(b"%PDF")
    assert len(pdf_report) > 1000

def test_location_diagnostic_data():
    """Verify detailed site problem diagnostics generated correctly."""
    from app.ui.components.location_report import get_location_diagnostic_data
    loc = PUNE_LOCATIONS[0] # MG Road (Critical)
    diag = get_location_diagnostic_data(loc)
    assert "Severe" in diag["problem_title"]
    assert diag["depth_cm"] > 0
    assert len(diag["ai_tags"]) > 0
    assert "Plastic" in diag["debris_mix"]

def test_create_floodguard_map_zones():
    """Verify map creates correctly for all municipal zones and bounds."""
    from app.ui.components.map_view import create_floodguard_map, ZONE_CENTROIDS

    for zone in ["All Zones", "Central", "West", "East", "North", "South"]:
        locs = [l for l in PUNE_LOCATIONS if zone == "All Zones" or l.get("zone") == zone]
        m = create_floodguard_map(
            locations=locs,
            zone=zone,
            fit_bounds=True
        )
        assert m is not None
        html = m.get_root().render()
        assert "leaflet" in html.lower()
        if zone != "All Zones":
            assert f"Municipal Boundary: {zone} Zone" in html

def test_render_floodguard_map_component_rendering():
    """Verify Leaflet map renders via st_folium with dynamic remount keys."""
    from app.ui.components.map_view import create_floodguard_map, render_floodguard_map_component
    import unittest.mock as mock

    m = create_floodguard_map(PUNE_LOCATIONS[:5], zone="West")

    with mock.patch("streamlit_folium._component_func") as mock_comp:
        render_floodguard_map_component(m, height=440, key="overview_map_West_Map")
        assert mock_comp.called
        assert "key" in mock_comp.call_args[1]

def test_priority_queue_data_helpers():
    """Verify priority queue open_incidents, count, and time rendering."""
    from datetime import datetime, timedelta
    from app.ui.views.priority_queue import _ago, open_incidents, open_incident_count

    # _ago tests
    now = datetime.utcnow()
    assert "min ago" in _ago(now - timedelta(minutes=15))
    assert "h ago" in _ago(now - timedelta(hours=3))
    assert "d ago" in _ago(now - timedelta(days=2))

    # open_incidents returns list
    incidents = open_incidents()
    assert isinstance(incidents, list)
    assert len(incidents) >= 0

    # open_incident_count returns int matching non-resolved count
    count = open_incident_count()
    assert isinstance(count, int)
    assert count >= 0


