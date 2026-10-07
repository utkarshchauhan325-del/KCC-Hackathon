import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
from app.ui.pune_data import (
    PUNE_LOCATIONS, KPIS, RECENT_ALERTS,
    RAINFALL_FORECAST, WATER_LEVEL_TREND,
    get_weather_adjusted_locations, get_live_pune_kpis,
    get_busiest_traffic_corridor
)
from app.core.weather_client import fetch_live_pune_weather
from app.ui.components.charts import (
    render_risk_distribution_donut,
    render_rainfall_forecast_bars,
    render_water_level_trend
)
import textwrap
from app.ui.components.map_view import create_floodguard_map, render_floodguard_map_component
from app.ui.components.location_report import render_location_full_report_box

def render_overview_dashboard():
    """Render the exact FloodGuard dashboard overview with live WeatherAPI & TomTom Traffic intelligence."""

    # Check if a location was clicked via URL query param (e.g. from score table)
    if hasattr(st, "query_params") and "inspect" in st.query_params and st.query_params["inspect"]:
        st.session_state["selected_location_id"] = st.query_params["inspect"]

    # Fetch live weather and calculate deterministic multi-attribute priority
    force_refresh = st.session_state.pop("force_weather_refresh", False)
    weather = fetch_live_pune_weather(force_refresh=force_refresh)
    locations = get_weather_adjusted_locations(force_refresh=force_refresh)
    kpis = get_live_pune_kpis(locations)
    top1 = locations[0]
    busiest = get_busiest_traffic_corridor(locations)

    # Top Header
    st.markdown(textwrap.dedent("""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>Flood & Traffic Gridlock Surveillance</h1>
            <p>Real-time multi-attribute risk monitoring, traffic intelligence & early warning system</p>
        </div>
        <div class="header-actions">
            <div class="search-mock">
                <span>🔍</span>
                <span>Search corridors, cameras, sensors...</span>
            </div>
            <div class="bell-badge">
                <span>🔔</span>
                <span class="bell-count">1</span>
            </div>
            <div class="avatar-badge">R</div>
            <div class="date-badge">📅 Oct 06, 2026 | Live Monitoring</div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # 4 Top KPI Cards with Sparklines (Dynamically Computed from Weather Intelligence)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(textwrap.dedent(f"""
        <div class="kpi-card">
            <div class="kpi-left">
                <div class="kpi-header">
                    <span class="kpi-icon" style="background:#FEE2E2; color:#DC2626;">⚠️</span>
                    <span class="kpi-title">Critical locations</span>
                </div>
                <div class="kpi-num-row">
                    <span class="kpi-value">{kpis['critical_locations']:02d}</span>
                    <span class="kpi-diff red">↑ {kpis['critical_diff'][1:]}</span>
                </div>
            </div>
            <svg class="kpi-sparkline" viewBox="0 0 80 30" fill="none">
                <path d="M2 24 L20 22 L40 18 L60 8 L78 2" stroke="#EF4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 24 L20 22 L40 18 L60 8 L78 2 L78 30 L2 30 Z" fill="rgba(239, 68, 68, 0.1)"/>
            </svg>
        </div>
        """), unsafe_allow_html=True)

    with col2:
        st.markdown(textwrap.dedent(f"""
        <div class="kpi-card">
            <div class="kpi-left">
                <div class="kpi-header">
                    <span class="kpi-icon" style="background:#FFEDD5; color:#EA580C;">📊</span>
                    <span class="kpi-title">High risk locations</span>
                </div>
                <div class="kpi-num-row">
                    <span class="kpi-value">{kpis['high_risk_locations']:02d}</span>
                    <span class="kpi-diff orange">↑ {kpis['high_risk_diff'][1:]}</span>
                </div>
            </div>
            <svg class="kpi-sparkline" viewBox="0 0 80 30" fill="none">
                <path d="M2 26 L22 20 L42 22 L62 12 L78 6" stroke="#F97316" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 26 L22 20 L42 22 L62 12 L78 6 L78 30 L2 30 Z" fill="rgba(249, 115, 22, 0.1)"/>
            </svg>
        </div>
        """), unsafe_allow_html=True)

    with col3:
        st.markdown(textwrap.dedent(f"""
        <div class="kpi-card">
            <div class="kpi-left">
                <div class="kpi-header">
                    <span class="kpi-icon" style="background:#DBEAFE; color:#2563EB;">💧</span>
                    <span class="kpi-title">Active waterlogging</span>
                </div>
                <div class="kpi-num-row">
                    <span class="kpi-value">{kpis['active_waterlogging']:02d}</span>
                    <span class="kpi-diff blue">↑ {kpis['active_waterlogging_diff'][1:]}</span>
                </div>
            </div>
            <svg class="kpi-sparkline" viewBox="0 0 80 30" fill="none">
                <path d="M2 28 L24 24 L44 14 L64 16 L78 8" stroke="#3B82F6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 28 L24 24 L44 14 L64 16 L78 8 L78 30 L2 30 Z" fill="rgba(59, 130, 246, 0.1)"/>
            </svg>
        </div>
        """), unsafe_allow_html=True)

    with col4:
        st.markdown(textwrap.dedent(f"""
        <div class="kpi-card">
            <div class="kpi-left">
                <div class="kpi-header">
                    <span class="kpi-icon" style="background:#FEF3C7; color:#D97706;">〰️</span>
                    <span class="kpi-title">Drainage risk</span>
                </div>
                <div class="kpi-num-row">
                    <span class="kpi-value">{kpis['drainage_risk']:02d}</span>
                    <span class="kpi-diff amber">↑ {kpis['drainage_risk_diff'][1:]}</span>
                </div>
            </div>
            <svg class="kpi-sparkline" viewBox="0 0 80 30" fill="none">
                <path d="M2 25 L20 20 L40 24 L60 16 L78 10" stroke="#F59E0B" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 25 L20 20 L40 24 L60 16 L78 10 L78 30 L2 30 Z" fill="rgba(245, 158, 11, 0.1)"/>
            </svg>
        </div>
        """), unsafe_allow_html=True)

    st.write("")

    # Middle Section: Map on Left (45%), Table on Right (55%)
    # Synchronize selected zone between Emergency Ranking and Geospatial Map
    selected_zone = st.session_state.get("dashboard_zone_filter", "All Zones")
    zone_filtered_locs = locations if selected_zone == "All Zones" else [l for l in locations if l.get("zone") == selected_zone]

    map_col, table_col = st.columns([1, 1.25], gap="medium")

    with map_col:
        # Map control header
        m_head1, m_head2 = st.columns([2, 1])
        with m_head1:
            zone_badge = f"<span style='font-size:12px; color:#0284C7; font-weight:700; background:#E0F2FE; padding:2px 8px; border-radius:6px; border:1px solid #BAE6FD;'>{selected_zone}</span>" if selected_zone != "All Zones" else ""
            st.markdown(f"<div style='display:flex; align-items:center; gap:8px;'><h3 style='margin:0; font-size:18px; font-weight:800; color:#0F172A;'>📍 Pune Geospatial Surveillance</h3>{zone_badge}</div>", unsafe_allow_html=True)
        with m_head2:
            layer_mode = st.radio("Layer", ["Map", "Satellite"], horizontal=True, label_visibility="collapsed", key="overview_layer_mode")

        # Create Folium GIS map synchronized with selected municipal zone
        m = create_floodguard_map(
            locations=zone_filtered_locs,
            zone=selected_zone,
            layer_type=layer_mode,
            selected_location_id=st.session_state.get("selected_location_id"),
            fit_bounds=True
        )
        map_data = render_floodguard_map_component(
            m,
            height=440,
            key=f"overview_map_{selected_zone}_{layer_mode}"
        )

        # Detect clicked marker on map
        if map_data:
            clicked_pt = map_data.get("last_object_clicked") or map_data.get("last_clicked")
            if clicked_pt and isinstance(clicked_pt, dict) and "lat" in clicked_pt and "lng" in clicked_pt:
                c_lat = round(clicked_pt["lat"], 5)
                c_lng = round(clicked_pt["lng"], 5)
                click_key = (c_lat, c_lng)
                if st.session_state.get("last_handled_map_click") != click_key:
                    st.session_state["last_handled_map_click"] = click_key
                    closest = min(locations, key=lambda l: (l["lat"] - c_lat)**2 + (l["lng"] - c_lng)**2)
                    dist_sq = (closest["lat"] - c_lat)**2 + (closest["lng"] - c_lng)**2
                    if dist_sq < 0.005:
                        if st.session_state.get("selected_location_id") != closest["id"]:
                            st.session_state["selected_location_id"] = closest["id"]
                            st.rerun()

        # Map Bottom Legend
        legend_html = textwrap.dedent("""
        <div style="display:flex; justify-content:space-between; align-items:center; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:8px 14px; margin-top:8px;">
            <div style="display:flex; align-items:center; gap:14px; font-size:12px; color:#475569;">
                <b>Risk Level:</b>
                <span><span style="color:#EF4444; font-size:14px;">●</span> Critical</span>
                <span><span style="color:#F97316; font-size:14px;">●</span> High</span>
                <span><span style="color:#F59E0B; font-size:14px;">●</span> Medium</span>
                <span><span style="color:#10B981; font-size:14px;">●</span> Low</span>
            </div>
            <div style="font-size:11px; color:#94A3B8;">0 ── 2.5 ── 5 km</div>
        </div>
        """).strip()
        st.markdown(legend_html, unsafe_allow_html=True)


    with table_col:
        t_head1, t_head2 = st.columns([3, 1.5])
        with t_head1:
            st.markdown("""
            <div style="margin-bottom:6px;">
                <h3 style="margin:0; font-size:18px; font-weight:800; color:#0F172A;">Multi-Attribute Emergency Ranking</h3>
                <p style="margin:2px 0 0 0; font-size:12px; color:#64748B;">Ranked on: 🌧️ Precip (mm) + 🚗 Traffic Gridlock (%) + 💧 Conduit (%) + 🪨 Blockage (%)</p>
            </div>
            """, unsafe_allow_html=True)
        with t_head2:
            zone_filter = st.selectbox(
                "Filter Zone",
                ["All Zones", "Central", "West", "East", "North", "South"],
                key="dashboard_zone_filter",
                label_visibility="collapsed"
            )

        # Filter locations
        filtered_locs = locations
        if zone_filter != "All Zones":
            filtered_locs = [l for l in locations if l.get("zone") == zone_filter]

        # Top key locations to display prominently
        display_locs = filtered_locs[:8]

        # Build compact, elegant HTML table with clickable rows
        active_hotspot_id = st.session_state.get("selected_location_id")

        table_rows_html = ""
        for loc in display_locs:
            r_level = loc["risk_level"]
            pill_class = f"pill-{r_level.lower()}"
            fill_class = f"fill-{r_level.lower()}"
            p_val = loc.get("precip_mm", loc["rainfall_3h"])
            comp_score = loc.get("composite_score", loc["risk_score"])
            is_active = (loc["id"] == active_hotspot_id)
            row_active_cls = " active-corridor-row" if is_active else ""
            inspect_href = f"?inspect={loc['id']}#diagnostic-report-box"

            table_rows_html += f"""<tr class="ranking-row{row_active_cls}">
<td style="font-weight:600; color:#1E293B;">
<a href="{inspect_href}" target="_self" class="cell-link" title="Open diagnostic report for {loc['name']}">
<span style="display:inline-block; width:22px; font-weight:800; color:{'#2563EB' if is_active else '#7C3AED'}; font-size:11px;">
{'📍' if is_active else f"#{loc.get('priority_rank', '-')}"}
</span>
<span style="{'color:#1D4ED8; font-weight:700;' if is_active else ''}">{loc['name']}</span>
</a>
</td>
<td>
<a href="{inspect_href}" target="_self" class="cell-link">
<span class="pill-badge {pill_class}">{r_level}</span>
</a>
</td>
<td style="text-align:center;">
<a href="{inspect_href}" target="_self" class="cell-link">
<span style="font-weight:800; color:#0F172A; font-size:12px;">{comp_score}</span>
</a>
</td>
<td>
<a href="{inspect_href}" target="_self" class="cell-link">
<span style="background:#EFF6FF; border:1px solid #BFDBFE; color:#1D4ED8; font-weight:800; font-size:11px; padding:2px 7px; border-radius:6px; display:inline-block; white-space:nowrap;">
🌧️ {p_val} mm
</span>
</a>
</td>
<td>
<a href="{inspect_href}" target="_self" class="cell-link">
<div style="display:flex; align-items:center; gap:6px;">
<span style="font-weight:600; font-size:11px; width:28px;">{loc['water_level_pct']}%</span>
<div class="progress-track" style="width:55px; height:7px; display:inline-block;">
<div class="progress-fill {fill_class}" style="width:{loc['water_level_pct']}%;"></div>
</div>
</div>
</a>
</td>
<td style="text-align:center;">
<a href="{inspect_href}" target="_self" class="cell-link">
<span style="font-weight:700; color:#475569; font-size:11px;">{loc['blockage_pct']}%</span>
</a>
</td>
</tr>"""

        compact_table_html = f"""<style>
.ranking-table-card {{
background: #FFFFFF;
border: 1px solid #E2E8F0;
border-radius: 10px;
padding: 6px 10px;
box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}}
.ranking-html-table {{
width: 100%;
border-collapse: collapse;
text-align: left;
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}}
.ranking-html-table th {{
padding: 7px 6px;
font-size: 11px;
color: #64748B;
font-weight: 700;
border-bottom: 1px solid #E2E8F0;
white-space: nowrap;
}}
.ranking-html-table td {{
padding: 6px 6px;
border-bottom: 1px solid #F1F5F9;
font-size: 12px;
vertical-align: middle;
}}
.ranking-html-table tr:last-child td {{
border-bottom: none;
}}
.ranking-row {{
transition: background 0.15s ease;
}}
.ranking-row:hover {{
background: #F8FAFC !important;
cursor: pointer;
}}
.active-corridor-row {{
background: #EFF6FF !important;
border-left: 3px solid #2563EB;
}}
.cell-link {{
text-decoration: none !important;
color: inherit !important;
display: block;
}}
.cell-link:hover {{
text-decoration: none !important;
}}
.pill-badge {{
display: inline-block;
padding: 2px 7px;
border-radius: 8px;
font-size: 10px;
font-weight: 700;
text-transform: uppercase;
letter-spacing: 0.02em;
}}
.pill-critical {{ background-color: #FEE2E2; color: #DC2626; border: 1px solid #FECACA; }}
.pill-high {{ background-color: #FFEDD5; color: #EA580C; border: 1px solid #FED7AA; }}
.pill-medium {{ background-color: #FEF3C7; color: #D97706; border: 1px solid #FDE68A; }}
.pill-low {{ background-color: #DCFCE7; color: #16A34A; border: 1px solid #BBF7D0; }}
.progress-track {{
background: #F1F5F9;
border-radius: 4px;
overflow: hidden;
}}
.progress-fill {{ border-radius: 4px; height: 100%; }}
.fill-critical {{ background: #EF4444; }}
.fill-high {{ background: #F97316; }}
.fill-medium {{ background: #FBBF24; }}
.fill-low {{ background: #10B981; }}
</style>
<div class="ranking-table-card">
<table class="ranking-html-table">
<thead>
<tr>
<th>Rank & Corridor</th>
<th>Severity</th>
<th style="text-align:center;">Score</th>
<th>Precip</th>
<th>Conduit Saturation</th>
<th style="text-align:center;">Blockage</th>
</tr>
</thead>
<tbody>
{table_rows_html}
</tbody>
</table>
<div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #F1F5F9; padding-top:6px; margin-top:4px; font-size:11px; color:#64748B;">
<span>👆 Click any corridor above or map dot to open diagnostic report</span>
<span>Top {len(display_locs)} corridors ({selected_zone})</span>
</div>
</div>"""
        st.html(compact_table_html)

    # -------------------------------------------------------------
    # SITE PROBLEM & DIAGNOSTIC REPORT BOX (COMPACT 5-KPI CARD)
    # -------------------------------------------------------------
    active_hotspot_id = st.session_state.get("selected_location_id")
    if active_hotspot_id:
        active_loc = next((l for l in locations if l["id"] == active_hotspot_id), None)
        if active_loc:
            # Trigger smooth scroll to the diagnostic report box
            import streamlit.components.v1 as components
            components.html("""
            <script>
            setTimeout(function() {
                try {
                    const el = window.parent.document.getElementById('diagnostic-report-box');
                    if (el) {
                        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                } catch(e) {}
            }, 150);
            </script>
            """, height=0)
            render_location_full_report_box(active_loc)

    st.markdown("<hr style='border:none; border-top:1px solid #E2E8F0; margin:24px 0;'>", unsafe_allow_html=True)

    # Middle Bottom Charts: Risk Distribution (Donut) & Rainfall Forecast (Bar)
    c1, c2 = st.columns([1, 1], gap="medium")

    with c1:
        st.markdown("""
        <div class="fg-card">
            <h4 class="fg-card-title">Risk Distribution</h4>
            <p class="fg-card-sub">Proportion of locations categorized by real-time severity</p>
        """, unsafe_allow_html=True)
        donut_fig = render_risk_distribution_donut()
        st.plotly_chart(donut_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="fg-card">
            <h4 class="fg-card-title">Rainfall Forecast (Next 24h)</h4>
            <p class="fg-card-sub">IMD Doppler radar & telemetry precipitation projection</p>
        """, unsafe_allow_html=True)
        bar_fig = render_rainfall_forecast_bars()
        st.plotly_chart(bar_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # Bottom Row: Water Level Trend (Line) & Recent Alerts
    b1, b2 = st.columns([1.2, 1], gap="medium")

    with b1:
        st.markdown("""
        <div class="fg-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h4 class="fg-card-title">Water Level Trend</h4>
                    <p class="fg-card-sub">Telemetry comparison across high-risk corridors</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        trend_fig = render_water_level_trend()
        st.plotly_chart(trend_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with b2:
        st.markdown("""
        <div class="fg-card" style="height:290px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <h4 class="fg-card-title" style="margin:0;">Recent Alerts</h4>
                <a href="#" style="font-size:12px; font-weight:700; color:#2563EB; text-decoration:none;">View all →</a>
            </div>
            <p class="fg-card-sub" style="margin-bottom:12px;">Active municipal warning dispatches & sensor thresholds</p>
        """, unsafe_allow_html=True)

        for alert in RECENT_ALERTS:
            st.markdown(textwrap.dedent(f"""
            <div class="alert-item">
                <span class="alert-dot">{alert['icon']}</span>
                <div class="alert-content">
                    <p class="alert-title">{alert['title']}</p>
                    <p class="alert-subtitle">{alert['subtitle']}</p>
                </div>
                <span class="alert-time">{alert['time']}</span>
            </div>
            """), unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
