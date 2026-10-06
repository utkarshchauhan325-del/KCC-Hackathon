"""Live Risk Map View - Full GIS spatial analysis across Pune Municipal wards."""

import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
from app.ui.pune_data import PUNE_LOCATIONS, CCTV_CAMERAS, get_weather_adjusted_locations
from app.ui.components.map_view import create_floodguard_map

import textwrap

def render_live_risk_map():
    """Render full interactive GIS risk map with layers and filters."""

    st.markdown(textwrap.dedent("""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>Live Risk Map & GIS Surveillance</h1>
            <p>Geospatial telemetry, catchment basins, and live hydraulic stage monitoring</p>
        </div>
        <div class="header-actions">
            <div class="date-badge">🟢 WeatherAPI GIS Sync Active</div>
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

    # Filter toolbar
    c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1.5])
    with c1:
        zone = st.selectbox("Municipal Zone", ["All Zones", "Central", "West", "East", "North", "South"])
    with c2:
        risk_filter = st.multiselect("Severity Filter", ["Critical", "High", "Medium", "Low"], default=["Critical", "High"])
    with c3:
        layer_mode = st.radio("Basemap Layer", ["Map", "Satellite"], horizontal=True)
    with c4:
        show_cameras = st.checkbox("Overlay CCTV Cameras (6)", value=True)

    # Filter data with real-time weather adjusted priority
    filtered = get_weather_adjusted_locations()
    if zone != "All Zones":
        filtered = [l for l in filtered if l["zone"] == zone]
    if risk_filter:
        filtered = [l for l in filtered if l["risk_level"] in risk_filter]

    # Map container
    m = create_floodguard_map(
        locations=filtered,
        center_lat=18.5240,
        center_lng=73.8550,
        zoom_start=13,
        layer_type=layer_mode
    )

    st_folium(m, height=560, use_container_width=True, returned_objects=[])

    # Summary metrics below map
    st.markdown("### 📊 Active Filter Spatial Summary")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Visible Locations", len(filtered))
    crit_count = len([l for l in filtered if l["risk_level"] == "Critical"])
    mc2.metric("Critical Hotspots", crit_count)
    avg_water = int(sum(l["water_level_pct"] for l in filtered) / max(len(filtered), 1))
    mc3.metric("Avg Water Capacity", f"{avg_water}%")
    avg_blockage = int(sum(l["blockage_pct"] for l in filtered) / max(len(filtered), 1))
    mc4.metric("Avg Debris Blockage", f"{avg_blockage}%")
