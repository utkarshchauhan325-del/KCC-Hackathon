"""Risk map view: monitored locations across Pune municipal zones."""

import streamlit as st
from app.ui.pune_data import CCTV_CAMERAS, get_weather_adjusted_locations
from app.ui.components.map_view import create_floodguard_map, render_floodguard_map_component
from app.ui.components.styles import chip, icon, page_header


ZONE_TITLES = {
    "All Zones": "All zones",
    "Central": "Central zone: Camp, Shivajinagar, Deccan, Swargate, Railway Station",
    "West": "West zone: Kothrud, Karve Road, Baner, Aundh, Pashan, Bavdhan",
    "East": "East zone: Viman Nagar, Kharadi, Hadapsar, Magarpatta, Yerwada",
    "North": "North zone: PCMC, Bhosari, Dapodi, Sangvi, Vishrantwadi",
    "South": "South zone: Katraj, Bibwewadi, Dhankawadi, Kondhwa, Sinhagad Road",
}


def render_live_risk_map():
    """Render the interactive risk map with zone, severity, basemap and camera filters."""

    st.markdown(page_header(
        "Risk map",
        "Monitored drains and corridors, coloured by current severity. Filter by zone and overlay camera positions.",
        eyebrow="Map",
    ), unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1.5], vertical_alignment="bottom")
    with c1:
        zone = st.selectbox("Zone", ["All Zones", "Central", "West", "East", "North", "South"], key="live_risk_map_zone")
    with c2:
        risk_filter = st.multiselect("Severity", ["Critical", "High", "Medium", "Low"], default=["Critical", "High", "Medium", "Low"], key="live_risk_map_risk")
    with c3:
        layer_mode = st.radio("Basemap", ["Map", "Satellite"], horizontal=True, key="live_risk_map_layer")
    with c4:
        show_cameras = st.checkbox(f"Show CCTV cameras ({len(CCTV_CAMERAS)})", value=True, key="live_risk_map_cctv")

    all_locations = get_weather_adjusted_locations()
    filtered = all_locations
    if zone != "All Zones":
        filtered = [l for l in filtered if l.get("zone") == zone]
    if risk_filter:
        filtered = [l for l in filtered if l.get("risk_level") in risk_filter]

    cams_in_zone = len([c for c in CCTV_CAMERAS if zone == "All Zones" or c.get("zone") == zone])
    st.markdown(
        f'<div class="fg-card" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;padding:10px 16px;margin:8px 0 12px 0;">'
        f'<div style="display:flex;align-items:center;gap:10px;color:#0A7C8F;">{icon("pin", 16)}'
        f'<div><div style="font-size:13.5px;font-weight:600;color:#0B1220;">{ZONE_TITLES.get(zone, zone)}</div>'
        f'<div style="font-size:12px;color:#64708A;">Showing <span class="fg-mono">{len(filtered)}</span> locations</div></div></div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;">{chip(f"<b>{cams_in_zone}</b> cameras in view")}</div></div>',
        unsafe_allow_html=True,
    )

    m = create_floodguard_map(
        locations=filtered,
        zone=zone,
        layer_type=layer_mode,
        show_cctv=show_cameras,
        cctv_cameras=CCTV_CAMERAS,
        fit_bounds=True
    )
    render_floodguard_map_component(m, height=580, key=f"live_risk_map_{zone}_{layer_mode}_{show_cameras}_{len(filtered)}")

    st.write("")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Locations shown", len(filtered))
    crit_count = len([l for l in filtered if l.get("risk_level") == "Critical"])
    mc2.metric("Critical", crit_count)
    avg_water = int(sum(l.get("water_level_pct", 0) for l in filtered) / max(len(filtered), 1))
    mc3.metric("Avg conduit saturation", f"{avg_water}%")
    avg_blockage = int(sum(l.get("blockage_pct", 0) for l in filtered) / max(len(filtered), 1))
    mc4.metric("Avg blockage", f"{avg_blockage}%")
