"""Overview Dashboard View - Matches FloodGuard Municipal Intelligence Screenshot."""

import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
from app.ui.pune_data import (
    PUNE_LOCATIONS, KPIS, RECENT_ALERTS,
    RAINFALL_FORECAST, WATER_LEVEL_TREND
)
from app.ui.components.charts import (
    render_risk_distribution_donut,
    render_rainfall_forecast_bars,
    render_water_level_trend
)
from app.ui.components.map_view import create_floodguard_map

def render_overview_dashboard():
    """Render the exact FloodGuard dashboard overview."""

    # Top Header
    st.markdown("""
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
            <div class="date-badge">📅 Sep 24, 2026 | 10:24 AM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4 Top KPI Cards with Sparklines
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-left">
                <div class="kpi-header">
                    <span class="kpi-icon" style="background:#FEE2E2; color:#DC2626;">⚠️</span>
                    <span class="kpi-title">Critical locations</span>
                </div>
                <div class="kpi-num-row">
                    <span class="kpi-value">{KPIS['critical_locations']:02d}</span>
                    <span class="kpi-diff red">↑ {KPIS['critical_diff'][1:]}</span>
                </div>
            </div>
            <svg class="kpi-sparkline" viewBox="0 0 80 30" fill="none">
                <path d="M2 24 L20 22 L40 18 L60 8 L78 2" stroke="#EF4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 24 L20 22 L40 18 L60 8 L78 2 L78 30 L2 30 Z" fill="rgba(239, 68, 68, 0.1)"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-left">
                <div class="kpi-header">
                    <span class="kpi-icon" style="background:#FFEDD5; color:#EA580C;">📊</span>
                    <span class="kpi-title">High risk locations</span>
                </div>
                <div class="kpi-num-row">
                    <span class="kpi-value">{KPIS['high_risk_locations']:02d}</span>
                    <span class="kpi-diff orange">↑ {KPIS['high_risk_diff'][1:]}</span>
                </div>
            </div>
            <svg class="kpi-sparkline" viewBox="0 0 80 30" fill="none">
                <path d="M2 26 L22 20 L42 22 L62 12 L78 6" stroke="#F97316" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 26 L22 20 L42 22 L62 12 L78 6 L78 30 L2 30 Z" fill="rgba(249, 115, 22, 0.1)"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-left">
                <div class="kpi-header">
                    <span class="kpi-icon" style="background:#DBEAFE; color:#2563EB;">💧</span>
                    <span class="kpi-title">Active waterlogging</span>
                </div>
                <div class="kpi-num-row">
                    <span class="kpi-value">{KPIS['active_waterlogging']:02d}</span>
                    <span class="kpi-diff blue">↑ {KPIS['active_waterlogging_diff'][1:]}</span>
                </div>
            </div>
            <svg class="kpi-sparkline" viewBox="0 0 80 30" fill="none">
                <path d="M2 28 L24 24 L44 14 L64 16 L78 8" stroke="#3B82F6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 28 L24 24 L44 14 L64 16 L78 8 L78 30 L2 30 Z" fill="rgba(59, 130, 246, 0.1)"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-left">
                <div class="kpi-header">
                    <span class="kpi-icon" style="background:#FEF3C7; color:#D97706;">〰️</span>
                    <span class="kpi-title">Drainage risk</span>
                </div>
                <div class="kpi-num-row">
                    <span class="kpi-value">{KPIS['drainage_risk']:02d}</span>
                    <span class="kpi-diff amber">↑ {KPIS['drainage_risk_diff'][1:]}</span>
                </div>
            </div>
            <svg class="kpi-sparkline" viewBox="0 0 80 30" fill="none">
                <path d="M2 25 L20 20 L40 24 L60 16 L78 10" stroke="#F59E0B" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 25 L20 20 L40 24 L60 16 L78 10 L78 30 L2 30 Z" fill="rgba(245, 158, 11, 0.1)"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)

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

        # Create and render map
        m = create_floodguard_map(
            locations=PUNE_LOCATIONS,
            center_lat=18.5240,
            center_lng=73.8550,
            zoom_start=12,
            layer_type=layer_mode
        )
        st_folium(m, height=440, use_container_width=True, returned_objects=[])

        # Map Bottom Legend
        st.markdown("""
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
        """, unsafe_allow_html=True)

    with table_col:
        t_head1, t_head2 = st.columns([3, 1.5])
        with t_head1:
            st.markdown("""
            <div style="margin-bottom:6px;">
                <h3 style="margin:0; font-size:18px; font-weight:800; color:#0F172A;">Flood Risk by Location</h3>
                <p style="margin:2px 0 0 0; font-size:12px; color:#64748B;">Risk level, rainfall and water level across key municipal locations</p>
            </div>
            """, unsafe_allow_html=True)
        with t_head2:
            zone_filter = st.selectbox(
                "Filter Zone",
                ["All Zones", "Central", "West", "East", "North", "South"],
                label_visibility="collapsed"
            )

        # Filter locations
        filtered_locs = PUNE_LOCATIONS
        if zone_filter != "All Zones":
            filtered_locs = [l for l in PUNE_LOCATIONS if l["zone"] == zone_filter]

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

            status_class = f"st-{loc['status'].lower()}"

            table_rows_html += f"""
            <tr style="border-bottom: 1px solid #F1F5F9; font-size:12px;">
                <td style="padding:10px 8px; font-weight:600; color:#1E293B;">{loc['name']}</td>
                <td style="padding:10px 8px;"><span class="pill-badge {pill_class}">{r_level}</span></td>
                <td style="padding:10px 8px; font-weight:600; color:#334155;">{loc['rainfall_3h']}</td>
                <td style="padding:10px 8px; min-width:140px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-weight:600; font-size:11px; width:30px;">{loc['water_level_pct']}%</span>
                        <div class="progress-track">
                            <div class="progress-fill {fill_class}" style="width:{loc['water_level_pct']}%;"></div>
                        </div>
                    </div>
                </td>
                <td style="padding:10px 8px; font-weight:800; color:{trend_color}; font-size:14px; text-align:center;">{trend_icon}</td>
                <td style="padding:10px 8px;"><span class="{status_class}">{loc['status']}</span></td>
                <td style="padding:10px 8px; color:#94A3B8; text-align:right; cursor:pointer;">⋮</td>
            </tr>
            """

        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; overflow-x:auto; padding:4px 10px;">
            <table style="width:100%; border-collapse:collapse; text-align:left;">
                <thead>
                    <tr style="border-bottom:1px solid #E2E8F0; font-size:11px; color:#64748B; font-weight:700;">
                        <th style="padding:8px 8px;">Location</th>
                        <th style="padding:8px 8px;">Risk Level</th>
                        <th style="padding:8px 8px;">Rainfall<br><span style="font-weight:400; font-size:10px;">(mm/3h)</span></th>
                        <th style="padding:8px 8px;">Water Level<br><span style="font-weight:400; font-size:10px;">(% of capacity)</span></th>
                        <th style="padding:8px 8px; text-align:center;">Trend<br><span style="font-weight:400; font-size:10px;">(24h)</span></th>
                        <th style="padding:8px 8px;">Status</th>
                        <th style="padding:8px 8px;"></th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)

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
            st.markdown(f"""
            <div class="alert-item">
                <span class="alert-dot">{alert['icon']}</span>
                <div class="alert-content">
                    <p class="alert-title">{alert['title']}</p>
                    <p class="alert-subtitle">{alert['subtitle']}</p>
                </div>
                <span class="alert-time">{alert['time']}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
