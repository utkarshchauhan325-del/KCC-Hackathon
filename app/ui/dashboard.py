"""FloodGuard - flood and drainage operations console for Pune Municipal Corporation."""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
from app.db.session import init_db
from app.ui.components.styles import BRAND_MARK, get_floodguard_css
from app.core.weather_client import fetch_live_pune_weather
from app.ui.views.overview import render_overview_dashboard
from app.ui.views.live_map import render_live_risk_map
from app.ui.views.cctv_monitoring import render_cctv_monitoring
from app.ui.views.priority_queue import open_incident_count, render_priority_queue_and_interventions
from app.ui.views.flood_analytics import render_flood_analytics

# Initialize SQLite/PostgreSQL Database
init_db()

st.set_page_config(
    page_title="FloodGuard | Pune Municipal Corporation",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_floodguard_css(), unsafe_allow_html=True)

# -------------------------------------------------------------
# Pages
# -------------------------------------------------------------
PAGE_SPECS = [
    ("overview", "Dashboard", ":material/dashboard:",
     "City risk summary, ranked corridors and forecasts", render_overview_dashboard),
    ("risk-map", "Risk Map", ":material/map:",
     "Monitored locations by zone, severity and camera", render_live_risk_map),
    ("cctv", "CCTV Analysis", ":material/videocam:",
     "Camera feeds and video analysis for drains and dumping", render_cctv_monitoring),
    ("queue", "Priority Queue", ":material/assignment_late:",
     "Officer review, open incidents and crew dispatch", render_priority_queue_and_interventions),
    ("analytics", "Analytics & Reports", ":material/query_stats:",
     "Rainfall correlation, ward comparison and exports", render_flood_analytics),
]

pages = {
    slug: st.Page(fn, title=title, url_path=slug, default=(slug == "overview"))
    for slug, title, _ico, _desc, fn in PAGE_SPECS
}
current = st.navigation(list(pages.values()), position="hidden")
current_slug = next((s for s, p in pages.items() if p.url_path == current.url_path), "overview")

# -------------------------------------------------------------
# Proper Sidebar Navigation Panel
# -------------------------------------------------------------
with st.sidebar:
    # PMC Disaster Management Brand
    st.markdown(
        f"""
        <div class="fg-sb-brand">
            <div class="fg-sb-logo">{BRAND_MARK}</div>
            <div>
                <div class="fg-sb-title">FloodGuard</div>
                <div class="fg-sb-org">Pune Municipal Corporation &middot; Disaster Cell</div>
            </div>
        </div>
        <div class="fg-sb-status">
            <span class="fg-sb-pulse"></span>
            <span class="fg-sb-stat-text">SYSTEM OPERATIONAL &middot; SENSORS LIVE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="fg-sb-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="fg-sb-nav-label">COMMAND CONSOLE</div>', unsafe_allow_html=True)

    # Navigation Links with Material Icons and Badge
    queue_open = open_incident_count()
    for slug, title, ico, _desc, _fn in PAGE_SPECS:
        badge_text = f" ({queue_open} open)" if slug == "queue" and queue_open > 0 else ""
        st.page_link(
            pages[slug],
            label=f"{title}{badge_text}",
            icon=ico,
            use_container_width=True
        )



# -------------------------------------------------------------
# Top Operational Strip (Main Area)
# -------------------------------------------------------------
active_spec = next((item for item in PAGE_SPECS if item[0] == current_slug), PAGE_SPECS[0])
st.markdown(
    f"""
    <div class="fg-top-strip">
        <div class="fg-top-strip-left">
            <span class="fg-top-tag">PMC DISASTER MANAGEMENT CELL</span>
            <span class="fg-top-sep">&middot;</span>
            <span class="fg-top-zone">{active_spec[1].upper()} VIEW</span>
        </div>
        <div class="fg-top-strip-right">
            <span class="fg-top-clock">{datetime.now():%d %b %Y &middot; %H:%M IST}</span>
            <span class="fg-top-dot"></span>
            <span class="fg-top-active">LIVE FEEDS SYNCHRONIZED</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

current.run()
