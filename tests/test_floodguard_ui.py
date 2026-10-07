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
from app.ui.views.flood_analytics import generate_printable_html_report

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
    donut = render_risk_distribution_donut()
    assert len(donut.data) == 1
    assert donut.data[0].type == "pie"

    bars = render_rainfall_forecast_bars()
    assert len(bars.data) == 1
    assert bars.data[0].type == "bar"

    lines = render_water_level_trend()
    assert len(lines.data) == 3  # MG Road, FC Road, Projected

    corr = render_7day_rainfall_water_correlation()
    assert len(corr.data) == 2

    ward_bars = render_ward_vulnerability_bars()
    assert len(ward_bars.data) == 3

    scatter = render_blockage_vs_flood_scatter()
    assert len(scatter.data) == 1

def test_printable_html_report_generation():
    """Verify official report generation contains required metadata."""
    html_report = generate_printable_html_report()
    assert "Pune Municipal Corporation" in html_report
    assert "Disaster Management Cell" in html_report
    assert "MG Road Junction" in html_report
    assert "FC Road Junction" in html_report
    assert "Deccan Gymkhana" in html_report

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

def test_render_floodguard_map_html_resizing():
    """Verify Leaflet map html includes invalidateSize listener."""
    from app.ui.components.map_view import create_floodguard_map
    import folium

    m = create_floodguard_map(PUNE_LOCATIONS[:5], zone="West")
    html = m.get_root().render()
    assert "invalidateSize" not in html # Raw folium doesn't have it

    # Check that our injection logic works
    from app.ui.components.map_view import render_floodguard_map_component
    import unittest.mock as mock

    with mock.patch("streamlit.components.v1.html") as mock_html:
        render_floodguard_map_component(m, height=440)
        assert mock_html.called
        rendered_content = mock_html.call_args[0][0]
        assert "invalidateSize" in rendered_content
        assert "triggerResize" in rendered_content


