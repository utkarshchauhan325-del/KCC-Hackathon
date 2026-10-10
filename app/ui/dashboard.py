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
    initial_sidebar_state="collapsed",
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
# Top navigation bar
# -------------------------------------------------------------
NAV_LABELS = {"overview": "Dashboard", "risk-map": "Risk Map", "cctv": "CCTV", "queue": "Queue", "analytics": "Analytics"}
queue_open = open_incident_count()

with st.container(key="fg_topnav"):
    cols = st.columns([2.6] + [1] * len(PAGE_SPECS) + [2.2], vertical_alignment="center", gap="small")
    cols[0].markdown(
        f'''<div class="fg-nav-brand"><div class="fg-sb-logo">{BRAND_MARK}</div>
        <div><div class="fg-nav-title">FloodGuard</div><div class="fg-nav-org">Pune Municipal Corporation</div></div></div>''',
        unsafe_allow_html=True,
    )
    for col, (slug, title, ico, desc, _fn) in zip(cols[1:], PAGE_SPECS):
        label = NAV_LABELS.get(slug, title)
        if slug == "queue" and queue_open:
            label = f"{label} ({queue_open})"
        state = "active" if slug == current_slug else "idle"
        with col.container(key=f"fgnav_{state}_{slug.replace('-', '_')}"):
            st.page_link(pages[slug], label=label, icon=ico, help=desc)
    cols[-1].markdown(
        f'''<div class="fg-nav-status"><span class="fg-top-dot"></span>
        <span class="fg-nav-clock">{datetime.now():%d %b &middot; %H:%M} IST</span></div>''',
        unsafe_allow_html=True,
    )

current.run()
