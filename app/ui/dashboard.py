"""FloodGuard - flood and drainage operations console for Pune Municipal Corporation."""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
from app.db.session import init_db
from app.ui.components.styles import BRAND_MARK, get_floodguard_css, icon
from app.ui.pune_data import PRIORITY_QUEUE
from app.ui.views.overview import render_overview_dashboard
from app.ui.views.live_map import render_live_risk_map
from app.ui.views.cctv_monitoring import render_cctv_monitoring
from app.ui.views.priority_queue import render_priority_queue_and_interventions
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
# (slug, title, short label, icon, description, function, badge)
PAGE_SPECS = [
    ("overview", "Overview", "Overview", "grid",
     "City risk summary, ranked corridors and forecasts", render_overview_dashboard, None),
    ("risk-map", "Risk map", "Risk map", "map",
     "Monitored locations by zone, severity and camera", render_live_risk_map, None),
    ("cctv", "CCTV analysis", "CCTV", "camera",
     "Camera feeds and video analysis for drains and dumping", render_cctv_monitoring, None),
    ("queue", "Priority queue", "Queue", "queue",
     "Officer review, open incidents and crew dispatch", render_priority_queue_and_interventions, len(PRIORITY_QUEUE)),
    ("analytics", "Analytics and reports", "Analytics", "chart",
     "Rainfall correlation, ward comparison and exports", render_flood_analytics, None),
]

pages = {
    slug: st.Page(fn, title=title, url_path=slug, default=(slug == "overview"))
    for slug, title, _short, _ico, _desc, fn, _badge in PAGE_SPECS
}
current = st.navigation(list(pages.values()), position="hidden")
current_slug = next((s for s, p in pages.items() if p.url_path == current.url_path), "overview")

# -------------------------------------------------------------
# Top bar: brand, inline links (wide screens) and pop-up menu
# -------------------------------------------------------------
with st.container(key="fg_topbar", horizontal=True, vertical_alignment="center", gap="small"):
    with st.container(key="fg_brand"):
        st.markdown(
            f'<div class="fg-brand">{BRAND_MARK}<div>'
            f'<div class="fg-brand-name">FloodGuard</div>'
            f'<div class="fg-brand-org">Pune Municipal Corporation &middot; Disaster Management Cell</div>'
            f"</div></div>",
            unsafe_allow_html=True,
        )

    with st.container(key="fg_links", horizontal=True, vertical_alignment="center", gap=None):
        for slug, _title, short, _ico, _desc, _fn, _badge in PAGE_SPECS:
            state = "on" if slug == current_slug else "off"
            with st.container(key=f"nav{state}_{slug.replace('-', '_')}"):
                st.page_link(pages[slug], label=short)

    st.html(f'<div class="fg-clock">{datetime.now():%d %b %Y &middot; %H:%M}</div>')

    menu = st.popover("Menu", icon=":material/menu:")
    with menu:
        st.html(
            '<div class="fg-pal-head"><span class="fg-pal-title">Go to</span>'
            '<span class="fg-pal-title">5 sections</span></div>'
        )
        for slug, title, _short, ico, desc, _fn, badge in PAGE_SPECS:
            state = "on_" if slug == current_slug else ""
            with st.container(key=f"pal_{state}{slug.replace('-', '_')}", gap=None):
                st.page_link(pages[slug], label=title)
                badge_html = f'<span class="fg-pal-count">{badge} open</span>' if badge else ""
                st.markdown(
                    f'<div class="fg-pal-ico">{icon(ico, 15)}</div>'
                    f'<div class="fg-pal-desc">{desc}</div>{badge_html}',
                    unsafe_allow_html=True,
                )
        st.html(
            '<div class="fg-pal-foot"><span>Pune Municipal Corporation</span>'
            '<span>Zone: Central</span></div>'
        )

current.run()
