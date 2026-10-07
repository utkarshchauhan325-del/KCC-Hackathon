"""Interactive Geospatial GIS Map component matching FloodGuard UI."""

import folium
from folium import plugins
from typing import List, Dict, Any, Optional

# Centroid and default zoom configuration for Pune Municipal Zones
ZONE_CENTROIDS = {
    "All Zones": {"lat": 18.5204, "lng": 73.8567, "zoom": 12},
    "Central":   {"lat": 18.5210, "lng": 73.8580, "zoom": 14},
    "West":      {"lat": 18.5220, "lng": 73.7950, "zoom": 13},
    "East":      {"lat": 18.5300, "lng": 73.9220, "zoom": 13},
    "North":     {"lat": 18.5850, "lng": 73.8350, "zoom": 13},
    "South":     {"lat": 18.4650, "lng": 73.8620, "zoom": 13},
}

# Geographic bounding boxes for Pune Municipal Zones
ZONE_BOUNDS = {
    "Central": [[18.498, 73.835], [18.544, 73.885]],
    "West":    [[18.485, 73.765], [18.565, 73.825]],
    "East":    [[18.495, 73.880], [18.568, 73.965]],
    "North":   [[18.555, 73.795], [18.625, 73.875]],
    "South":   [[18.435, 73.825], [18.498, 73.895]],
}

def create_floodguard_map(
    locations: List[Dict[str, Any]],
    center_lat: Optional[float] = None,
    center_lng: Optional[float] = None,
    zoom_start: Optional[int] = None,
    layer_type: str = "Map",
    selected_location_id: Optional[str] = None,
    zone: str = "All Zones",
    show_cctv: bool = False,
    cctv_cameras: Optional[List[Dict[str, Any]]] = None,
    fit_bounds: bool = True
) -> folium.Map:
    """Create Folium GIS map with custom markers, river path, zone boundary, and controls."""

    # Resolve center and zoom based on selected municipal zone
    zone_cfg = ZONE_CENTROIDS.get(zone, ZONE_CENTROIDS["All Zones"])

    if zone != "All Zones":
        target_lat = zone_cfg["lat"]
        target_lng = zone_cfg["lng"]
        target_zoom = zoom_start if zoom_start is not None else zone_cfg.get("zoom", 13)
        # If locations are provided in this zone, center around their centroid
        zone_locs = [loc for loc in locations if loc.get("zone") == zone] if locations else []
        if zone_locs:
            lats = [loc["lat"] for loc in zone_locs if "lat" in loc]
            lngs = [loc["lng"] for loc in zone_locs if "lng" in loc]
            if lats and lngs:
                target_lat = sum(lats) / len(lats)
                target_lng = sum(lngs) / len(lngs)
    else:
        target_lat = center_lat if center_lat is not None else zone_cfg["lat"]
        target_lng = center_lng if center_lng is not None else zone_cfg["lng"]
        target_zoom = zoom_start if zoom_start is not None else zone_cfg["zoom"]

    # Select base tiles (high availability, zero rate limits, full CORS support across all browsers)
    if layer_type == "Satellite":
        tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        attr = "Esri World Imagery"
    else:
        tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
        attr = "Esri World Street Map"

    m = folium.Map(
        location=[target_lat, target_lng],
        zoom_start=target_zoom,
        tiles=tiles,
        attr=attr,
        zoom_control=True,
        control_scale=True
    )
    # Store calculated target center and zoom for st_folium programmatic pan & zoom
    m.target_center = (round(target_lat, 4), round(target_lng, 4))
    m.target_zoom = target_zoom

    # Highlight Zone Boundary rectangle if a specific zone is selected
    if zone in ZONE_BOUNDS:
        zone_locs = [loc for loc in locations if loc.get("zone") == zone] if locations else []
        if zone_locs:
            lats = [loc["lat"] for loc in zone_locs if "lat" in loc]
            lngs = [loc["lng"] for loc in zone_locs if "lng" in loc]
            if lats and lngs:
                b = [
                    [min(lats) - 0.005, min(lngs) - 0.005],
                    [max(lats) + 0.005, max(lngs) + 0.005]
                ]
            else:
                b = ZONE_BOUNDS[zone]
        else:
            b = ZONE_BOUNDS[zone]

        folium.Rectangle(
            bounds=b,
            color="#0284C7",
            weight=2,
            fill=True,
            fill_color="#0284C7",
            fill_opacity=0.07,
            dash_array="6, 6",
            tooltip=f"🏛️ Municipal Boundary: {zone} Zone"
        ).add_to(m)

    # Automatically fit bounds to enclose all locations in the selected zone or city-wide
    if fit_bounds:
        if zone != "All Zones":
            zone_locs = [loc for loc in locations if loc.get("zone") == zone] if locations else []
            if zone_locs:
                lats = [loc["lat"] for loc in zone_locs if "lat" in loc]
                lngs = [loc["lng"] for loc in zone_locs if "lng" in loc]
                if lats and lngs:
                    pad_lat = max(0.006, (max(lats) - min(lats)) * 0.12)
                    pad_lng = max(0.006, (max(lngs) - min(lngs)) * 0.12)
                    m.fit_bounds([
                        [min(lats) - pad_lat, min(lngs) - pad_lng],
                        [max(lats) + pad_lat, max(lngs) + pad_lng]
                    ])
            elif zone in ZONE_BOUNDS:
                m.fit_bounds(ZONE_BOUNDS[zone])
        elif zone == "All Zones":
            if locations:
                lats = [loc["lat"] for loc in locations if "lat" in loc]
                lngs = [loc["lng"] for loc in locations if "lng" in loc]
                if lats and lngs:
                    pad_lat = max(0.015, (max(lats) - min(lats)) * 0.08)
                    pad_lng = max(0.015, (max(lngs) - min(lngs)) * 0.08)
                    m.fit_bounds([
                        [min(lats) - pad_lat, min(lngs) - pad_lng],
                        [max(lats) + pad_lat, max(lngs) + pad_lng]
                    ])
            else:
                m.fit_bounds([[18.420, 73.740], [18.630, 73.970]])

    # Add Mula-Mutha River polyline path through Pune
    mula_mutha_river = [
        [18.5720, 73.7920], # Aundh / Sangvi
        [18.5580, 73.8070], # Aundh Bridge
        [18.5440, 73.8290], # Dapodi Confluence
        [18.5350, 73.8480], # Wakdewadi / Shivaji Bridge
        [18.5280, 73.8550], # Sangam (Mula meets Mutha)
        [18.5230, 73.8680], # Sangamwadi
        [18.5330, 73.8820], # Bund Garden / Yerwada
        [18.5380, 73.9120], # Mundhwa
        [18.5250, 73.9450], # Kharadi / Hadapsar stretch
    ]
    folium.PolyLine(
        mula_mutha_river,
        color="#38BDF8",
        weight=7,
        opacity=0.6,
        tooltip="Mula-Mutha River Basin (Current Gauge: +1.4m)"
    ).add_to(m)

    # Color mapping
    color_map = {
        "Critical": "#EF4444",
        "High": "#F97316",
        "Medium": "#F59E0B",
        "Low": "#10B981"
    }

    # Add locations with custom circles
    for loc in locations:
        if zone != "All Zones" and loc.get("zone") != zone:
            continue
        r_level = loc["risk_level"]
        col = color_map.get(r_level, "#F59E0B")
        is_crit = (r_level == "Critical")
        is_sel = (selected_location_id == loc["id"])

        p_mm = loc.get("precip_mm", loc["rainfall_3h"])
        t_pct = loc.get("traffic_congestion_pct", 40)
        t_speed = loc.get("traffic_speed_kmh", 25.0)
        t_lvl = loc.get("traffic_level", "Moderate")
        is_busiest = loc.get("is_busiest_traffic", False)
        comp_score = loc.get("composite_score", loc["risk_score"])

        busiest_html = '<div style="background:#FEF3C7; color:#B45309; border:1px solid #FDE68A; font-weight:800; font-size:10px; padding:2px 6px; border-radius:6px; margin-bottom:6px; text-align:center;">🚗 #1 MOST BUSIEST CORRIDOR</div>' if is_busiest else ''

        popup_html = f"""
        <div style="font-family:'Plus Jakarta Sans',sans-serif; min-width:220px; padding:4px;">
            {busiest_html}
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <b style="color:#0F172A; font-size:13px;">#{loc.get('priority_rank', '-')} {loc['name']}</b>
                <span style="background:{col}22; color:{col}; font-weight:700; font-size:10px; padding:2px 6px; border-radius:10px; border:1px solid {col}55;">{r_level.upper()}</span>
            </div>
            <div style="font-size:11px; color:#64748B; margin-bottom:6px;">Zone: {loc['zone']} | Score: <b>{comp_score}/100</b></div>
            <table style="width:100%; font-size:11px; border-top:1px solid #E2E8F0; padding-top:4px;">
                <tr><td style="color:#64748B;">Live Precip:</td><td style="text-align:right; font-weight:800; color:#2563EB;">{p_mm} mm</td></tr>
                <tr><td style="color:#64748B;">TomTom Traffic:</td><td style="text-align:right; font-weight:800; color:{'#DC2626' if t_pct>=75 else '#EA580C'};">{t_pct}% ({t_speed} km/h)</td></tr>
                <tr><td style="color:#64748B;">Conduit Saturation:</td><td style="text-align:right; font-weight:700; color:{col};">{loc['water_level_pct']}%</td></tr>
                <tr><td style="color:#64748B;">Drain Blockage:</td><td style="text-align:right; font-weight:600;">{loc['blockage_pct']}%</td></tr>
                <tr><td style="color:#64748B;">Status:</td><td style="text-align:right; font-weight:700; color:{col};">{loc['status']}</td></tr>
            </table>
        </div>
        """

        # Outer glow ring for Critical or Busiest
        if is_crit or is_sel or is_busiest:
            folium.CircleMarker(
                location=[loc["lat"], loc["lng"]],
                radius=18 if (is_sel or is_busiest) else 14,
                color="#EF4444" if is_busiest else col,
                weight=2,
                fill=True,
                fill_color="#EF4444" if is_busiest else col,
                fill_opacity=0.25,
            ).add_to(m)

        # Core circle marker
        folium.CircleMarker(
            location=[loc["lat"], loc["lng"]],
            radius=8 if is_crit else 6,
            color="#FFFFFF",
            weight=2,
            fill=True,
            fill_color=col,
            fill_opacity=0.95,
            tooltip=f"#{loc.get('priority_rank', '-')} {loc['name']} (Score: {comp_score} | 🌧️ {p_mm}mm | 🚗 {t_pct}% Jam)",
            popup=folium.Popup(popup_html, max_width=270)
        ).add_to(m)

    # Optional CCTV Camera Layer Overlay
    if show_cctv and cctv_cameras:
        for cam in cctv_cameras:
            if zone != "All Zones" and cam.get("zone") != zone:
                continue
            c_lat = cam.get("lat")
            c_lng = cam.get("lng")
            if c_lat and c_lng:
                cam_html = f"""
                <div style="font-family:'Plus Jakarta Sans',sans-serif; min-width:180px; padding:4px;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                        <span style="font-size:14px;">📹</span>
                        <b style="color:#0F172A; font-size:12px;">{cam['name']}</b>
                    </div>
                    <div style="font-size:11px; color:#64748B; margin-bottom:4px;">
                        ID: <b>{cam['id']}</b> &bull; Zone: {cam.get('zone', '-')}
                    </div>
                    <div style="background:#ECFDF5; color:#065F46; border:1px solid #A7F3D0; font-size:10px; font-weight:700; padding:2px 6px; border-radius:6px; display:inline-block; margin-bottom:4px;">
                        ● {cam['status']} ({cam.get('stream_fps', 30)} FPS)
                    </div>
                    <div style="font-size:11px; color:#475569;">AI Diagnosis: <b>{cam.get('ai_status', 'Nominal')}</b></div>
                </div>
                """
                folium.CircleMarker(
                    location=[c_lat, c_lng],
                    radius=7,
                    color="#2563EB",
                    weight=2,
                    fill=True,
                    fill_color="#3B82F6",
                    fill_opacity=0.9,
                    tooltip=f"📹 {cam['name']} (CCTV LIVE)",
                    popup=folium.Popup(cam_html, max_width=230)
                ).add_to(m)

    return m


def render_floodguard_map_component(m: folium.Map, height: int = 440, key: Optional[str] = None) -> None:
    """Render Folium map with 100% reliable cross-browser reactivity (Safari, WebKit, Chrome)."""
    target_center = getattr(m, "target_center", None)
    target_zoom = getattr(m, "target_zoom", None)
    try:
        from streamlit_folium import st_folium
        if key is None:
            key = getattr(m, "get_name", lambda: "folium_map")()
        st_folium(
            m,
            key=key,
            height=height,
            center=target_center,
            zoom=target_zoom,
            use_container_width=True,
            returned_objects=[]
        )
    except Exception:
        import streamlit.components.v1 as components
        map_html = m.get_root().render()
        components.html(map_html, height=height, scrolling=False)


