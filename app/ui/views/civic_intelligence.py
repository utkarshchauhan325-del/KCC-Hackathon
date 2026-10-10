"""Civic Intelligence View - Real-time web intelligence powered by TinyFish API.

Monitors live web announcements, official PMC and IMD flood advisories, road closures,
drainage bottlenecks, and citizen online complaints across Pune municipal zones.
"""

from __future__ import annotations

import streamlit as st
from app.core.tinyfish_client import (
    fetch_pune_civic_intelligence,
    get_tinyfish_api_key,
)
from app.ui.components.styles import (
    ACCENT,
    INK,
    MUTED,
    STATUS,
    icon,
    page_header,
    section_title,
    status_pill,
)

CATEGORY_COLORS = {
    "Official Advisory": {"bg": "#EFF6FF", "fg": "#1D4ED8", "border": "#BFDBFE"},
    "Road Closure": {"bg": "#FEF2F2", "fg": "#DC2626", "border": "#FECACA"},
    "Drainage Issue": {"bg": "#FFF7ED", "fg": "#C2410C", "border": "#FFEDD5"},
    "Citizen Complaint": {"bg": "#FAF5FF", "fg": "#7E22CE", "border": "#E9D5FF"},
}

PRESET_QUERIES = {
    "All Pune Alerts": "pune flood advisory rainfall waterlogging road closure drainage complaint",
    "Dam & River Discharge": "pune khadakwasla dam discharge mutha river flood alert riverside evacuation",
    "Road Closures & Traffic": "pune waterlogging submerged road closure underpass traffic diversion",
    "Drainage & Clogged Drains": "pune stormwater drain choked nullah overflowing gutter silt blockage",
    "Citizen Online Reports": "pune rain waterlogging complaint citizen resident twitter facebook news",
}


def _render_kpi_card(label: str, value: int, sub: str, icon_name: str, color: str) -> str:
    return f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:16px 18px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.04em; color:{MUTED};">{label}</span>
            <span style="color:{color};">{icon(icon_name, 16)}</span>
        </div>
        <div style="font-size:28px; font-weight:700; color:{INK}; line-height:1.1; margin-bottom:4px;">{value:02d}</div>
        <div style="font-size:12px; color:{MUTED};">{sub}</div>
    </div>
    """


def render_civic_intelligence():
    """Render the Civic Intelligence & Public Pulse console."""
    st.markdown(
        page_header(
            "Civic Intelligence & Public Pulse",
            "Real-time web monitoring powered by TinyFish: official PMC and IMD flood advisories, road closures, drainage choke-points, and citizen online complaints.",
        ),
        unsafe_allow_html=True,
    )

    api_key = get_tinyfish_api_key()

    # API Status Banner
    st.markdown(
        """
        <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:10px 16px; margin-bottom:20px; display:flex; align-items:center; gap:8px;">
            <span style="height:9px; width:9px; border-radius:50%; background:#16A34A; display:inline-block;"></span>
            <span style="font-size:13px; font-weight:600; color:#15803D;">TinyFish is live</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Search query state
    if "civic_intel_query" not in st.session_state:
        st.session_state["civic_intel_query"] = PRESET_QUERIES["All Pune Alerts"]

    # Filter Controls row
    with st.container():
        fcols = st.columns([2.5, 1.2, 0.8], vertical_alignment="bottom", gap="medium")
        selected_preset = fcols[0].selectbox(
            "Topic Preset",
            list(PRESET_QUERIES.keys()),
            index=0,
            key="sb_preset_intel",
        )
        custom_query = fcols[1].text_input(
            "Filter by Specific Area / Locality",
            placeholder="e.g. Dighi, Kothrud, Sinhagad Road",
            key="txt_custom_filter",
        )
        refresh_btn = fcols[2].button(
            "Refresh Feed",
            icon=":material/refresh:",
            use_container_width=True,
            type="primary",
            key="btn_refresh_intel",
        )

    loc_filter = custom_query.strip()
    active_query = PRESET_QUERIES[selected_preset]
    if loc_filter:
        active_query = f"{loc_filter} pune waterlogging flood rain drainage road"

    # Purge any stale mock fallback data from older sessions
    stale_keys = [
        k for k, v in list(st.session_state.items())
        if k.startswith("intel_data_") and isinstance(v, dict) and (v.get("source") == "cached_fallback" or any(r.get("id", "").startswith("tf-fallback") for r in v.get("reports", [])))
    ]
    for sk in stale_keys:
        st.session_state.pop(sk, None)

    # Fetch data (cached in session or triggered via refresh)
    cache_key = f"intel_data_{active_query}_{loc_filter}"
    if refresh_btn or cache_key not in st.session_state:
        spinner_msg = f"Querying TinyFish live search for {loc_filter.title()}..." if loc_filter else "Querying TinyFish live web search for Pune alerts..."
        with st.spinner(spinner_msg):
            data = fetch_pune_civic_intelligence(query=active_query, limit=20, location_filter=loc_filter)
            st.session_state[cache_key] = data
    else:
        data = st.session_state[cache_key]

    # Show actual API status if not healthy
    if data.get("status") == "missing_key":
        st.warning("⚠️ TinyFish API Key is not configured. Add TINYFISH_API_KEY in your .env file.")
    elif data.get("status") in ("auth_error", "api_error", "network_error"):
        st.error(f"⚠️ TinyFish Search API: {data.get('error', 'Error reaching endpoint')}")

    reports = data.get("reports", [])


    # Recalculate KPIs strictly for filtered reports
    counts = {
        "Total": len(reports),
        "Official Advisory": sum(1 for r in reports if r["category"] == "Official Advisory"),
        "Road Closure": sum(1 for r in reports if r["category"] == "Road Closure"),
        "Drainage Issue": sum(1 for r in reports if r["category"] == "Drainage Issue"),
        "Citizen Complaint": sum(1 for r in reports if r["category"] == "Citizen Complaint"),
        "Videos": sum(1 for r in reports if r.get("is_video")),
    }

    # Summary KPI Cards
    sub_label = f"Strictly For '{loc_filter.title()}'" if loc_filter else "Live Web & News Items"
    kcols = st.columns(4, gap="medium")
    kcols[0].markdown(
        _render_kpi_card("Total Reports", counts.get("Total", len(reports)), sub_label, "layers", ACCENT),
        unsafe_allow_html=True,
    )
    kcols[1].markdown(
        _render_kpi_card("Video Footage", counts.get("Videos", 0), "Ground Reels & Broadcasts", "film", "#DC2626"),
        unsafe_allow_html=True,
    )
    kcols[2].markdown(
        _render_kpi_card("Official Advisories", counts.get("Official Advisory", 0), "PMC & IMD Bulletins", "alert", "#1D4ED8"),
        unsafe_allow_html=True,
    )
    kcols[3].markdown(
        _render_kpi_card("Drainage & Closures", counts.get("Drainage Issue", 0) + counts.get("Road Closure", 0), "Choke-points & Diverts", "drop", "#C2410C"),
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Secondary filter by category / video
    cat_options = ["All Reports"]
    if counts.get("Videos", 0) > 0:
        cat_options.append("📹 Videos & Footage Only")
    cat_options.extend(["Official Advisory", "Road Closure", "Drainage Issue", "Citizen Complaint"])

    cat_filter = st.radio(
        "Filter by category",
        cat_options,
        horizontal=True,
        label_visibility="collapsed",
        key="rad_cat_filter",
    )

    filtered_reports = reports
    if cat_filter == "📹 Videos & Footage Only":
        filtered_reports = [r for r in reports if r.get("is_video")]
    elif cat_filter != "All Reports":
        filtered_reports = [r for r in reports if r.get("category") == cat_filter]

    heading_sub = f"{len(filtered_reports)} verified reports strictly for '{loc_filter.title()}'" if loc_filter else f"{len(filtered_reports)} verified reports"
    st.markdown(
        section_title("Monitored Intelligence Feed", heading_sub),
        unsafe_allow_html=True,
    )

    if not filtered_reports:
        if loc_filter:
            st.markdown(
                f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:32px 20px; text-align:center; margin-top:14px;">
                    <div style="font-size:24px; margin-bottom:8px;">📍</div>
                    <div style="font-size:16px; font-weight:600; color:{INK}; margin-bottom:6px;">No reports or videos found exclusively for &ldquo;{loc_filter}&rdquo;</div>
                    <div style="font-size:13px; color:{MUTED}; max-width:480px; margin:0 auto;">
                        All reports from other Pune areas have been filtered out. Try clearing the filter or searching another area.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No matching reports found for the selected category.")
        return

    # Render report cards in a clean 2-column responsive layout
    rcols = st.columns(2, gap="medium")
    for idx, report in enumerate(filtered_reports):
        col = rcols[idx % 2]
        cat = report.get("category", "Official Advisory")
        cstyle = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["Official Advisory"])
        sev = report.get("severity", "Medium")
        sev_color = STATUS.get(sev, STATUS["Medium"])["fg"]
        is_vid = report.get("is_video", False)
        embed_url = report.get("embed_url")

        # Sanitize location tags: if filtered, only show the entered place
        if loc_filter:
            display_locs = [loc for loc in report.get("locations", []) if loc_filter.lower() in loc.lower()]
            if not display_locs:
                display_locs = [loc_filter.strip().title()]
        else:
            display_locs = report.get("locations", ["Pune Urban"])

        loc_tags = "".join(
            f'<span style="background:#F1F5F9; color:#334155; font-size:11px; font-weight:500; padding:2px 8px; border-radius:12px; margin-right:6px;">📍 {loc}</span>'
            for loc in display_locs
        )

        video_pill = ""
        if is_vid:
            video_pill = """
            <span style="background:#FEF2F2; color:#DC2626; border:1px solid #FECACA; font-size:11px; font-weight:700; padding:2px 7px; border-radius:4px; text-transform:uppercase; letter-spacing:0.03em;">
                📹 Video Report
            </span>
            """

        link_text = "▶️ Watch Video Footage &rarr;" if is_vid else "Open Source Link &rarr;"

        card_html = f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:18px 20px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.02); display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                        <span style="background:{cstyle['bg']}; color:{cstyle['fg']}; border:1px solid {cstyle['border']}; font-size:11px; font-weight:600; padding:3px 8px; border-radius:4px; text-transform:uppercase; letter-spacing:0.03em;">
                            {cat}
                        </span>
                        {video_pill}
                        <span style="font-size:11px; font-weight:600; color:{sev_color};">
                            &bull; {sev} Severity
                        </span>
                    </div>
                    <span style="font-size:12px; color:{MUTED};">{report.get('date', '')}</span>
                </div>
                <h4 style="font-size:15px; font-weight:600; color:{INK}; line-height:1.35; margin:0 0 8px 0;">
                    {report.get('title', '')}
                </h4>
                <p style="font-size:13px; color:#475569; line-height:1.45; margin:0 0 12px 0;">
                    {report.get('snippet', '')}
                </p>
            </div>
            <div>
                <div style="margin-bottom:12px; display:flex; flex-wrap:wrap; gap:4px;">
                    {loc_tags}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #F1F5F9; padding-top:10px;">
                    <span style="font-size:12px; color:{MUTED}; font-weight:500;">
                        🌐 {report.get('site_name', 'Web')}
                    </span>
                    <a href="{report.get('url', '#')}" target="_blank" style="color:{ACCENT}; font-size:12px; font-weight:600; text-decoration:none;">
                        {link_text}
                    </a>
                </div>
            </div>
        </div>
        """
        col.markdown(card_html, unsafe_allow_html=True)

        # If it is an embeddable YouTube video, embed the video player directly below the card
        if embed_url:
            with col:
                with st.expander("▶️ Play Embedded Video Footage", expanded=False):
                    st.video(embed_url)

    # Explanation and Architecture note
    with st.expander("ℹ️ About TinyFish Civic Intelligence Architecture", expanded=False):
        st.markdown(
            """
            **How TinyFish Works with FloodGuard:**
            - **Autonomous Web Search**: TinyFish scans live search indexes and online sources for municipal keywords (flood alerts, rain forecasts, dam discharges, submerged underpasses, citizen complaints).
            - **Strict Separation**: TinyFish functions as an external intelligence sensor and does not interfere with the local CCTV video pipeline, YOLOE segmentation, BoT-SORT object tracking, or deterministic flood scoring formulas.
            - **Cross-Verification**: Field officers and municipal controllers can compare AI CCTV detections with incoming public reports and road closures to dispatch emergency dewatering and suction machinery.
            """
        )
