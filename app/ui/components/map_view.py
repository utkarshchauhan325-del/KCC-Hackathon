"""Interactive Geospatial GIS Map component matching FloodGuard UI."""

import folium
from folium import plugins
from typing import List, Dict, Any, Optional

def create_floodguard_map(
    locations: List[Dict[str, Any]],
    center_lat: float = 18.5240,
    center_lng: float = 73.8550,
    zoom_start: int = 12,
    layer_type: str = "Map",
    selected_location_id: Optional[str] = None
) -> folium.Map:
    """Create Folium GIS map with custom markers, river path, and controls."""

    # Select base tiles
    if layer_type == "Satellite":
        tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        attr = "Esri World Imagery"
    else:
        # Crisp clean light map tiles
        tiles = "CartoDB positron"
        attr = "CartoDB"

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=zoom_start,
        tiles=tiles,
        attr=attr,
        zoom_control=True,
        control_scale=True
    )

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
        r_level = loc["risk_level"]
        col = color_map.get(r_level, "#F59E0B")
        is_crit = (r_level == "Critical")
        is_sel = (selected_location_id == loc["id"])

        popup_html = f"""
        <div style="font-family:'Plus Jakarta Sans',sans-serif; min-width:180px; padding:4px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <b style="color:#0F172A; font-size:13px;">{loc['name']}</b>
                <span style="background:{col}22; color:{col}; font-weight:700; font-size:10px; padding:2px 6px; border-radius:10px; border:1px solid {col}55;">{r_level.upper()}</span>
            </div>
            <div style="font-size:11px; color:#64748B; margin-bottom:6px;">Zone: {loc['zone']} | {loc['ward']}</div>
            <table style="width:100%; font-size:11px; border-top:1px solid #E2E8F0; padding-top:4px;">
                <tr><td style="color:#64748B;">Water Level:</td><td style="text-align:right; font-weight:700; color:{col};">{loc['water_level_pct']}%</td></tr>
                <tr><td style="color:#64748B;">3h Rainfall:</td><td style="text-align:right; font-weight:600;">{loc['rainfall_3h']} mm</td></tr>
                <tr><td style="color:#64748B;">Drain Blockage:</td><td style="text-align:right; font-weight:600;">{loc['blockage_pct']}%</td></tr>
                <tr><td style="color:#64748B;">Status:</td><td style="text-align:right; font-weight:700; color:{col};">{loc['status']}</td></tr>
            </table>
        </div>
        """

        # Outer glow ring for Critical
        if is_crit or is_sel:
            folium.CircleMarker(
                location=[loc["lat"], loc["lng"]],
                radius=18 if is_sel else 14,
                color=col,
                weight=2,
                fill=True,
                fill_color=col,
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
            tooltip=f"{loc['name']} ({r_level} - {loc['water_level_pct']}%)",
            popup=folium.Popup(popup_html, max_width=250)
        ).add_to(m)

    return m
