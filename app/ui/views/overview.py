import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
from app.ui.pune_data import (
    PUNE_LOCATIONS, KPIS, RECENT_ALERTS,
    RAINFALL_FORECAST, WATER_LEVEL_TREND,
    get_weather_adjusted_locations, get_live_pune_kpis
)
from app.core.weather_client import fetch_live_pune_weather
from app.ui.components.charts import (
    render_risk_distribution_donut,
    render_rainfall_forecast_bars,
    render_water_level_trend
)
import textwrap
from app.ui.components.map_view import create_floodguard_map
from app.ui.components.location_report import render_location_full_report_box

def render_overview_dashboard():
    """Render the exact FloodGuard dashboard overview with live WeatherAPI intelligence."""

    # Fetch live weather and calculate deterministic flood priority
    force_refresh = st.session_state.pop("force_weather_refresh", False)
    weather = fetch_live_pune_weather(force_refresh=force_refresh)
    locations = get_weather_adjusted_locations(force_refresh=force_refresh)
    kpis = get_live_pune_kpis(locations)
    top1 = locations[0]

    # Top Header
    st.markdown(textwrap.dedent("""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>Flood Risk Overview</h1>
            <p>Real-time risk monitoring and early warning system</p>
        </div>
        <div class="header-actions">
            <div class="search-mock">
                <span>🔍</span>
                <span>Search locations, cameras...</span>
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

    # WeatherAPI Live Command & Early Flood Warning Bar
    col_w_info, col_w_btn = st.columns([4.2, 1], gap="small")
    with col_w_info:
        st.markdown(textwrap.dedent(f"""
        <div style="background:linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border:1px solid #334155; border-radius:12px; padding:12px 18px; margin-bottom:14px; box-shadow:0 4px 14px rgba(0,0,0,0.12); font-family:'Plus Jakarta Sans',sans-serif;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <span style="background:{'#10B98120' if weather.is_live else '#F59E0B20'}; color:{'#34D399' if weather.is_live else '#FBBF24'}; border:1px solid {'#10B98160' if weather.is_live else '#F59E0B60'}; font-size:11px; font-weight:800; padding:4px 10px; border-radius:14px; letter-spacing:0.04em; text-transform:uppercase;">
                        ● {'WeatherAPI Live Sync' if weather.is_live else 'Weather Baseline'}
                    </span>
                    <span style="color:#F8FAFC; font-size:13px; font-weight:600;">
                        🌡️ <b>{weather.temp_c}°C</b> ({weather.condition_text}) &nbsp;|&nbsp; 
                        💧 Humidity: <b>{weather.humidity}%</b> &nbsp;|&nbsp; 
                        🌧️ Max Rain Chance: <b style="color:#60A5FA;">{weather.max_rain_chance}%</b> &nbsp;|&nbsp; 
                        🌊 24h Projected Precip: <b>{weather.total_precip_mm} mm</b>
                    </span>
                </div>
                <div style="background:#EF444422; border:1px solid #EF444477; padding:4px 12px; border-radius:8px; font-size:12px;">
                    <span style="color:#F87171; font-weight:800;">🚨 #1 PRECIPITATION PRIORITY:</span>
                    <span style="color:#FFFFFF; font-weight:700;">{top1['name']} ({top1.get('precip_mm', 24.5)} mm)</span>
                    <span style="color:#FCA5A5; font-weight:600;">— {top1['flood_probability_pct']}% Flood Probability</span>
                </div>
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)
    with col_w_btn:
        st.write("")
        if st.button("🔄 Sync WeatherAPI", use_container_width=True, help="Fetch real-time radar & hourly rain predictions"):
            st.session_state["force_weather_refresh"] = True
            st.rerun()

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
    map_col, table_col = st.columns([1, 1.25], gap="medium")

    with map_col:
        # Map control header
        m_head1, m_head2 = st.columns([2, 1])
        with m_head1:
            st.markdown("### 📍 Pune Geospatial Surveillance")
        with m_head2:
            layer_mode = st.radio("Layer", ["Map", "Satellite"], horizontal=True, label_visibility="collapsed")

        # Ensure default selected hotspot
        if "selected_location_id" not in st.session_state or not st.session_state["selected_location_id"]:
            st.session_state["selected_location_id"] = locations[0]["id"]

        # Create and render map with selected hotspot highlighted
        m = create_floodguard_map(
            locations=locations,
            center_lat=18.5240,
            center_lng=73.8550,
            zoom_start=12,
            layer_type=layer_mode,
            selected_location_id=st.session_state.get("selected_location_id")
        )
        map_data = st_folium(
            m,
            height=440,
            use_container_width=True,
            returned_objects=["last_object_clicked", "last_clicked"],
            key="pune_flood_map_overview"
        )

        # Detect clicked marker on map
        if map_data:
            clicked_pt = map_data.get("last_object_clicked") or map_data.get("last_clicked")
            if clicked_pt and isinstance(clicked_pt, dict) and "lat" in clicked_pt and "lng" in clicked_pt:
                c_lat = clicked_pt["lat"]
                c_lng = clicked_pt["lng"]
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

        # Quick location picker dropdown right under the map legend
        loc_options = {l["id"]: f"#{l.get('priority_rank', idx)} 📍 {l['name']} ({l.get('precip_mm', l['rainfall_3h'])} mm | {l['risk_level'].upper()} | Flood: {l.get('flood_probability_pct', l['risk_score'])}%)" for idx, l in enumerate(locations[:20], 1)}
        curr_sel = st.session_state.get("selected_location_id") or locations[0]["id"]
        if curr_sel not in loc_options:
            c_loc = next((l for l in locations if l["id"] == curr_sel), None)
            if c_loc:
                loc_options[curr_sel] = f"#{c_loc.get('priority_rank', '-')} 📍 {c_loc['name']} ({c_loc.get('precip_mm', c_loc['rainfall_3h'])} mm | {c_loc['risk_level'].upper()})"

        chosen_id = st.selectbox(
            "🎯 Click any dot on map OR select hotspot to inspect report:",
            options=list(loc_options.keys()),
            index=list(loc_options.keys()).index(curr_sel) if curr_sel in loc_options else 0,
            format_func=lambda x: loc_options[x]
        )
        if chosen_id != st.session_state.get("selected_location_id"):
            st.session_state["selected_location_id"] = chosen_id
            st.rerun()


    with table_col:
        t_head1, t_head2 = st.columns([3, 1.5])
        with t_head1:
            st.markdown("""
            <div style="margin-bottom:6px;">
                <h3 style="margin:0; font-size:18px; font-weight:800; color:#0F172A;">Precipitation & Flood Priority Ranking</h3>
                <p style="margin:2px 0 0 0; font-size:12px; color:#64748B;">Ranked by real-time precipitation (mm) and conduit flood surcharge</p>
            </div>
            """, unsafe_allow_html=True)
        with t_head2:
            zone_filter = st.selectbox(
                "Filter Zone",
                ["All Zones", "Central", "West", "East", "North", "South"],
                label_visibility="collapsed"
            )

        # Filter locations
        filtered_locs = locations
        if zone_filter != "All Zones":
            filtered_locs = [l for l in locations if l["zone"] == zone_filter]

        # Top key locations to display prominently
        display_locs = filtered_locs[:8]

        # Build custom styled HTML table matching the screenshot
        table_rows_html = ""
        for loc in display_locs:
            r_level = loc["risk_level"]
            pill_class = f"pill-{r_level.lower()}"
            fill_class = f"fill-{r_level.lower()}"

            trend_icon = "↗" if loc["trend_24h"] == "up" else ("↘" if loc["trend_24h"] == "down" else "→")
            trend_color = "#DC2626" if loc["trend_24h"] == "up" else ("#16A34A" if loc["trend_24h"] == "down" else "#64748B")

            status_class = f"st-{loc['status'].lower().replace(' ', '-').replace('/', '-')}"
            flood_prob = loc.get("flood_probability_pct", loc["risk_score"])
            prob_color = "#DC2626" if flood_prob >= 65 else ("#EA580C" if flood_prob >= 45 else "#16A34A")
            p_val = loc.get("precip_mm", loc["rainfall_3h"])

            table_rows_html += f"""
            <tr>
                <td style="font-weight:600; color:#1E293B;">
                    <span style="display:inline-block; width:22px; font-weight:800; color:#7C3AED; font-size:11px;">#{loc.get('priority_rank', '-')}</span>
                    {loc['name']}
                </td>
                <td><span class="pill-badge {pill_class}">{r_level}</span></td>
                <td>
                    <span style="background:#EFF6FF; border:1px solid #BFDBFE; color:#1D4ED8; font-weight:800; font-size:12px; padding:2px 8px; border-radius:10px; display:inline-block;">
                        🌧️ {p_val} mm
                    </span>
                </td>
                <td style="font-weight:800; color:{prob_color};">{flood_prob}%</td>
                <td style="min-width:100px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-weight:600; font-size:11px; width:28px;">{loc['water_level_pct']}%</span>
                        <div class="progress-track">
                            <div class="progress-fill {fill_class}" style="width:{loc['water_level_pct']}%;"></div>
                        </div>
                    </div>
                </td>
                <td style="font-weight:800; color:{trend_color}; font-size:14px; text-align:center;">{trend_icon}</td>
                <td><span class="{status_class}">{loc['status']}</span></td>
            </tr>"""

        full_table_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                * {{ box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
                body {{ margin: 0; padding: 0; background: #FFFFFF; color: #1E293B; }}
                .table-container {{
                    border: 1px solid #E2E8F0;
                    border-radius: 10px;
                    padding: 6px 12px;
                    background: #FFFFFF;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    text-align: left;
                }}
                th {{
                    padding: 8px 6px;
                    font-size: 11px;
                    color: #64748B;
                    font-weight: 700;
                    border-bottom: 1px solid #E2E8F0;
                }}
                td {{
                    padding: 9px 6px;
                    border-bottom: 1px solid #F1F5F9;
                    font-size: 12px;
                }}
                tr:last-child td {{
                    border-bottom: none;
                }}
                .pill-badge {{
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 10px;
                    font-weight: 700;
                    text-transform: uppercase;
                }}
                .pill-critical {{ background-color: #FEE2E2; color: #DC2626; border: 1px solid #FECACA; }}
                .pill-high {{ background-color: #FFEDD5; color: #EA580C; border: 1px solid #FED7AA; }}
                .pill-medium {{ background-color: #FEF3C7; color: #D97706; border: 1px solid #FDE68A; }}
                .pill-low {{ background-color: #DCFCE7; color: #16A34A; border: 1px solid #BBF7D0; }}
                .progress-track {{
                    background: #F1F5F9;
                    border-radius: 6px;
                    height: 8px;
                    width: 65px;
                    overflow: hidden;
                    display: inline-block;
                }}
                .progress-fill {{ height: 100%; border-radius: 6px; }}
                .fill-critical {{ background: #EF4444; }}
                .fill-high {{ background: #F97316; }}
                .fill-medium {{ background: #FBBF24; }}
                .fill-low {{ background: #10B981; }}
                .st-severe-downpour-inundation {{ color: #DC2626; font-weight: 700; }}
                .st-waterlogging-imminent {{ color: #DC2626; font-weight: 700; }}
                .st-heavy-inflow-surcharge {{ color: #EA580C; font-weight: 700; }}
                .st-rising-rapidly {{ color: #EA580C; font-weight: 700; }}
                .st-moderate-runoff-flow {{ color: #D97706; font-weight: 600; }}
                .st-optimal-discharge {{ color: #16A34A; font-weight: 600; }}
            </style>
        </head>
        <body>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Rank & Location</th>
                            <th>Severity</th>
                            <th>Live Precip</th>
                            <th>Flood Prob</th>
                            <th>Conduit Saturation</th>
                            <th style="text-align:center;">Trend</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """
        import streamlit.components.v1 as components
        components.html(full_table_html, height=440, scrolling=True)

    # Full-Length Detailed Site Problem & Diagnostic Report Box
    active_hotspot_id = st.session_state.get("selected_location_id")
    if active_hotspot_id:
        active_loc = next((l for l in locations if l["id"] == active_hotspot_id), None)
        if active_loc:
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
