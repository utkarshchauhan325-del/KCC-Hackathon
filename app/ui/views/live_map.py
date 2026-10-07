"""Live Risk Map View - Full GIS spatial analysis across Pune Municipal wards."""

import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
from app.ui.pune_data import PUNE_LOCATIONS, CCTV_CAMERAS, get_weather_adjusted_locations
from app.ui.components.map_view import create_floodguard_map, render_floodguard_map_component

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
        zone = st.selectbox("Municipal Zone", ["All Zones", "Central", "West", "East", "North", "South"], key="live_risk_map_zone")
    with c2:
        risk_filter = st.multiselect("Severity Filter", ["Critical", "High", "Medium", "Low"], default=["Critical", "High", "Medium", "Low"], key="live_risk_map_risk")
    with c3:
        layer_mode = st.radio("Basemap Layer", ["Map", "Satellite"], horizontal=True, key="live_risk_map_layer")
    with c4:
        show_cameras = st.checkbox("Overlay CCTV Cameras (6)", value=True, key="live_risk_map_cctv")

    # Filter data with real-time weather adjusted priority
    all_locations = get_weather_adjusted_locations()
    filtered = all_locations
    if zone != "All Zones":
        filtered = [l for l in filtered if l.get("zone") == zone]
    if risk_filter:
        filtered = [l for l in filtered if l.get("risk_level") in risk_filter]

    # Zone Information Banner
    zone_titles = {
        "All Zones": "All Pune Municipal Zones (City-Wide GIS Surveillance)",
        "Central": "Central Zone (Camp, Shivajinagar, Deccan, Swargate, Railway Station)",
        "West": "West Zone (Kothrud, Karve Road, Baner, Aundh, Pashan, Bavdhan)",
        "East": "East Zone (Viman Nagar, Kharadi, Hadapsar, Magarpatta, Yerwada)",
        "North": "North Zone (PCMC, Bhosari, Dapodi, Sangvi, Vishrantwadi)",
        "South": "South Zone (Katraj, Bibwewadi, Dhankawadi, Kondhwa, Sinhagad Road)"
    }
    desc = zone_titles.get(zone, zone)

    st.markdown(textwrap.dedent(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:10px 18px; margin: 10px 0 16px 0; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div style="display:flex; align-items:center; gap:10px;">
            <span style="font-size:18px;">📍</span>
            <div>
                <b style="font-size:14px; color:#0F172A;">{desc}</b>
                <div style="font-size:12px; color:#64748B;">
                    Showing <b>{len(filtered)}</b> monitored telemetry points in this operational view
                </div>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="background:#0284C715; color:#0284C7; border:1px solid #0284C735; font-size:11px; font-weight:700; padding:4px 10px; border-radius:12px;">
                🎯 Auto-Framed to {zone}
            </span>
            <span style="background:#10B98115; color:#10B981; border:1px solid #10B98135; font-size:11px; font-weight:700; padding:4px 10px; border-radius:12px;">
                📹 {len([c for c in CCTV_CAMERAS if zone == 'All Zones' or c.get('zone') == zone])} CCTVs Linked
            </span>
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

    # Generate dynamic Folium map centered and bounded to the selected zone
    m = create_floodguard_map(
        locations=filtered,
        zone=zone,
        layer_type=layer_mode,
        show_cctv=show_cameras,
        cctv_cameras=CCTV_CAMERAS,
        fit_bounds=True
    )

    render_floodguard_map_component(m, height=580)

    # Summary metrics below map
    st.markdown("### 📊 Active Filter Spatial Summary")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Visible Locations", len(filtered))
    crit_count = len([l for l in filtered if l.get("risk_level") == "Critical"])
    mc2.metric("Critical Hotspots", crit_count)
    avg_water = int(sum(l.get("water_level_pct", 0) for l in filtered) / max(len(filtered), 1))
    mc3.metric("Avg Water Capacity", f"{avg_water}%")
    avg_blockage = int(sum(l.get("blockage_pct", 0) for l in filtered) / max(len(filtered), 1))
    mc4.metric("Avg Debris Blockage", f"{avg_blockage}%")
