import streamlit as st
from app.ui.pune_data import (
    RECENT_ALERTS,
    get_weather_adjusted_locations, get_live_pune_kpis,
    get_busiest_traffic_corridor
)
from app.core.weather_client import fetch_live_pune_weather
from app.ui.components.charts import (
    render_risk_distribution_donut,
    render_rainfall_forecast_bars,
    render_water_level_trend
)
from app.ui.components.map_view import create_floodguard_map, render_floodguard_map_component
from app.ui.components.location_report import render_location_full_report_box
from app.ui.components.styles import STATUS, chip, icon, page_header, section_title, status_pill

_CHART_CONFIG = {"displayModeBar": False}
_ALERT_COLORS = {
    "critical": STATUS["Critical"]["fg"],
    "high": STATUS["High"]["fg"],
    "medium": "#D4A106",
    "low": STATUS["Low"]["fg"],
}


def _kpi(label: str, value: int, delta: str, ico: str, color: str) -> str:
    return (
        f'<div class="fg-kpi" style="--kpi-c:{color}">'
        f'<div class="fg-kpi-label">{icon(ico, 15)}<span>{label}</span></div>'
        f'<div class="fg-kpi-row"><span class="fg-kpi-value">{value:02d}</span>'
        f'<span class="fg-kpi-delta"><b>{delta}</b> vs baseline</span></div>'
        f"</div>"
    )


def render_overview_dashboard():
    """City overview: KPIs, map, ranked corridors, forecasts and recent alerts."""

    # Clear any residual query param so it doesn't freeze the selection
    if hasattr(st, "query_params") and "inspect" in st.query_params:
        inspect_id = st.query_params.get("inspect")
        if inspect_id and "selected_location_id" not in st.session_state:
            st.session_state["selected_location_id"] = inspect_id
        try:
            del st.query_params["inspect"]
        except Exception:
            pass

    force_refresh = st.session_state.pop("force_weather_refresh", False)
    weather = fetch_live_pune_weather(force_refresh=force_refresh)
    locations = get_weather_adjusted_locations(force_refresh=force_refresh)
    kpis = get_live_pune_kpis(locations)
    busiest = get_busiest_traffic_corridor(locations)

    feed = chip('<span class="fg-dot"></span>Weather feed live', "ok") if weather.is_live else chip(
        '<span class="fg-dot"></span>Weather feed offline, using defaults', "warn")
    meta = [
        f"{icon('rain', 13)} Pune <b>{weather.temp_c:.0f}&deg;C</b> &middot; {weather.condition_text}",
        f"{icon('pin', 13)} <b>{len(locations)}</b> locations",
    ]
    st.markdown(
        page_header(
            "Flood and traffic overview",
            "Risk across monitored drains and corridors, ranked on rainfall, traffic, conduit saturation and blockage.",
            eyebrow="Overview",
            meta=meta,
        ).replace('<div class="fg-meta">', f'<div class="fg-meta">{feed}'),
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(_kpi("Critical locations", kpis["critical_locations"], kpis["critical_diff"], "alert", STATUS["Critical"]["fg"]), unsafe_allow_html=True)
    k2.markdown(_kpi("High-risk locations", kpis["high_risk_locations"], kpis["high_risk_diff"], "gauge", STATUS["High"]["fg"]), unsafe_allow_html=True)
    k3.markdown(_kpi("Active waterlogging", kpis["active_waterlogging"], kpis["active_waterlogging_diff"], "drop", "#0A7C8F"), unsafe_allow_html=True)
    k4.markdown(_kpi("Drains over 50% blocked", kpis["drainage_risk"], kpis["drainage_risk_diff"], "layers", "#9A7200"), unsafe_allow_html=True)

    st.write("")

    selected_zone = st.session_state.get("dashboard_zone_filter", "All Zones")
    zone_filtered_locs = locations if selected_zone == "All Zones" else [l for l in locations if l.get("zone") == selected_zone]

    # Side by side on wide screens; CSS stacks them when the window is narrow
    with st.container(key="fg_maprank"):
        map_col, table_col = st.columns([1, 1.25], gap="medium")

        with map_col:
            m_head1, m_head2 = st.columns([2, 1], vertical_alignment="bottom")
            with m_head1:
                zone_note = "" if selected_zone == "All Zones" else f"Filtered to {selected_zone} zone"
                st.markdown(section_title("Map", zone_note or "All zones"), unsafe_allow_html=True)
            with m_head2:
                layer_mode = st.radio("Layer", ["Map", "Satellite"], horizontal=True, label_visibility="collapsed", key="overview_layer_mode")

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
            if map_data:
                clicked_loc = None
                popup_val = map_data.get("last_object_clicked_popup") or map_data.get("last_object_clicked_tooltip")
                if popup_val and isinstance(popup_val, str):
                    for l in locations:
                        if l["name"] in popup_val or l["id"] in popup_val:
                            clicked_loc = l
                            break

                if not clicked_loc:
                    clicked_pt = map_data.get("last_object_clicked") or map_data.get("last_clicked")
                    if clicked_pt and isinstance(clicked_pt, dict) and "lat" in clicked_pt and "lng" in clicked_pt:
                        c_lat = clicked_pt["lat"]
                        c_lng = clicked_pt["lng"]
                        closest = min(locations, key=lambda l: (l["lat"] - c_lat)**2 + (l["lng"] - c_lng)**2)
                        dist_sq = (closest["lat"] - c_lat)**2 + (closest["lng"] - c_lng)**2
                        if dist_sq < 0.01:
                            clicked_loc = closest

                if clicked_loc and clicked_loc["id"] != st.session_state.get("selected_location_id"):
                    st.session_state["selected_location_id"] = clicked_loc["id"]
                    st.session_state["last_handled_map_click"] = clicked_loc["id"]
                    st.rerun()

            legend = "".join(
                f'<span style="display:inline-flex;align-items:center;gap:6px;"><i style="width:8px;height:8px;border-radius:50%;background:{c};display:inline-block"></i>{n}</span>'
                for n, c in [("Critical", STATUS["Critical"]["fg"]), ("High", STATUS["High"]["fg"]), ("Medium", "#D4A106"), ("Low", STATUS["Low"]["fg"])]
            )
            st.markdown(
                f'<div class="fg-card" style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:8px 14px;margin-top:8px;font-size:12px;color:#64708A;">'
                f'<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:center;">{legend}</div>'
                f'<span class="fg-mono" style="font-size:11px;">Click a marker to open its report</span></div>',
                unsafe_allow_html=True,
            )

        with table_col:
            t_head1, t_head2 = st.columns([3, 1.5], vertical_alignment="bottom")
            with t_head1:
                st.markdown(section_title(
                    "Corridor ranking",
                    "Composite of forecast rain, traffic, conduit saturation and blockage. Locations marked CCTV use their camera's analysed score.",
                ), unsafe_allow_html=True)
            with t_head2:
                zone_filter = st.selectbox(
                    "Filter zone",
                    ["All Zones", "Central", "West", "East", "North", "South"],
                    key="dashboard_zone_filter",
                    label_visibility="collapsed"
                )

            filtered_locs = locations
            if zone_filter != "All Zones":
                filtered_locs = [l for l in locations if l.get("zone") == zone_filter]
            display_locs = filtered_locs[:8]
            active_hotspot_id = st.session_state.get("selected_location_id")
            widths = [3.2, 1.2, 0.8, 1.1, 1.8, 0.9]

            with st.container(key="ranking_table_box"):
                h = st.columns(widths, vertical_alignment="center")
                for col, label, center in zip(h, ["Corridor", "Severity", "Score", "Rain 24h", "Saturation", "Blockage"],
                                              [False, False, True, False, False, True]):
                    align = "center" if center else "left"
                    col.markdown(f"<div class='fg-th' style='text-align:{align}'>{label}</div>", unsafe_allow_html=True)

                for loc in display_locs:
                    r_level = loc["risk_level"]
                    fill_class = f"fill-{r_level.lower()}"
                    p_val = loc.get("precip_mm", loc["rainfall_3h"])
                    comp_score = loc.get("composite_score", loc["risk_score"])
                    is_active = (loc["id"] == active_hotspot_id)

                    r_c1, r_c2, r_c3, r_c4, r_c5, r_c6 = st.columns(widths, vertical_alignment="center")
                    if r_c1.button(
                        f"{loc.get('priority_rank', '-')}. {loc['name']}" + (" · CCTV" if loc.get("cctv_camera") else ""),
                        key=f"corridor_btn_{loc['id']}",
                        type="primary" if is_active else "secondary",
                        use_container_width=True,
                        help=f"Open the site report for {loc['name']}"
                    ):
                        if st.session_state.get("selected_location_id") != loc['id']:
                            st.session_state["selected_location_id"] = loc['id']
                            st.rerun()

                    r_c2.markdown(status_pill(r_level), unsafe_allow_html=True)
                    r_c3.markdown(f"<div class='fg-num' style='text-align:center;font-weight:600;white-space:nowrap'>{comp_score}</div>", unsafe_allow_html=True)
                    r_c4.markdown(f"<span class='fg-num' style='white-space:nowrap'>{p_val} mm</span>", unsafe_allow_html=True)
                    r_c5.markdown(
                        f'<div style="display:flex;align-items:center;gap:8px;"><span class="fg-num" style="width:30px">{loc["water_level_pct"]}%</span>'
                        f'<div class="progress-track" style="flex:1;max-width:60px;min-width:24px;height:5px;"><div class="progress-fill {fill_class}" style="width:{loc["water_level_pct"]}%;"></div></div></div>',
                        unsafe_allow_html=True,
                    )
                    r_c6.markdown(f"<div class='fg-num' style='text-align:center'>{loc['blockage_pct']}%</div>", unsafe_allow_html=True)

                busiest_note = f" &middot; Heaviest traffic: {busiest.get('name')}" if isinstance(busiest, dict) and busiest.get('name') else ""
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;padding-top:8px;font-size:11.5px;color:#64708A;">'
                    f'<span>Select a corridor to open its site report{busiest_note}</span>'
                    f'<span class="fg-mono">Top {len(display_locs)} &middot; {zone_filter}</span></div>',
                    unsafe_allow_html=True,
                )

    # Site report for the selected corridor
    active_hotspot_id = st.session_state.get("selected_location_id")
    if active_hotspot_id:
        active_loc = next((l for l in locations if l["id"] == active_hotspot_id), None)
        if active_loc:
            import streamlit.components.v1 as components
            components.html("""
            <script>
            setTimeout(function() {
                try {
                    const el = window.parent.document.getElementById('diagnostic-report-box');
                    if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                } catch(e) {}
            }, 150);
            </script>
            """, height=0)
            render_location_full_report_box(active_loc)

    st.markdown("<hr class='fg-rule'>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1.4], gap="medium")
    with c1:
        with st.container(border=True):
            st.markdown(section_title("Risk distribution", "Share of monitored locations by severity"), unsafe_allow_html=True)
            st.plotly_chart(render_risk_distribution_donut(locations), use_container_width=True, config=_CHART_CONFIG)
    with c2:
        with st.container(border=True):
            st.markdown(section_title(
                "Rainfall forecast, next 24 hours",
                f"{weather.source} hourly forecast &middot; {weather.next_24h_precip_mm:.1f} mm expected, "
                f"peak chance of rain {weather.max_rain_chance}%",
            ), unsafe_allow_html=True)
            st.plotly_chart(render_rainfall_forecast_bars(weather.hourly_forecast), use_container_width=True, config=_CHART_CONFIG)

    b1, b2 = st.columns([1.4, 1], gap="medium")
    with b1:
        with st.container(border=True):
            watch = sorted(
                [l for l in locations if l.get("saturation_forecast")],
                key=lambda l: (l.get("projected_peak_pct", 0), l.get("water_level_pct", 0)),
                reverse=True,
            )[:3]
            outlook = " &middot; ".join(f"{l['name']}: {l['overflow_outlook'].lower()}" for l in watch)
            st.markdown(section_title(
                "Overflow forecast",
                f"Drain fill projected from the rain forecast, blockage and conduit size. {outlook}",
            ), unsafe_allow_html=True)
            st.plotly_chart(
                render_water_level_trend(
                    [(l["name"], l["water_level_pct"], l["saturation_forecast"]) for l in watch],
                    [h.time for h in weather.hourly_forecast],
                ),
                use_container_width=True, config=_CHART_CONFIG,
            )
    with b2:
        with st.container(border=True):
            st.markdown(section_title("Recent alerts", "Warnings and sensor threshold crossings"), unsafe_allow_html=True)
            rows = "".join(
                f'<div class="alert-item"><span class="alert-bar" style="background:{_ALERT_COLORS.get(a.get("severity", ""), "#94A0B4")}"></span>'
                f'<div class="alert-content"><p class="alert-title">{a["title"]}</p><p class="alert-subtitle">{a["subtitle"]}</p></div>'
                f'<span class="alert-time">{a["time"]}</span></div>'
                for a in RECENT_ALERTS
            )
            st.markdown(f"<div>{rows}</div>", unsafe_allow_html=True)
