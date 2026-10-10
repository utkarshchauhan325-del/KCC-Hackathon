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
from app.ui.views.login import render_login_page
from app.ui.views.overview import render_overview_dashboard
from app.ui.views.live_map import render_live_risk_map
from app.ui.views.cctv_monitoring import render_cctv_monitoring
from app.ui.views.priority_queue import render_priority_queue_and_interventions
from app.ui.views.flood_analytics import render_flood_analytics
from app.ui.views.worker_tasks import render_worker_tasks_view
from app.ui.views.worker_task_detail import render_worker_task_detail_view
from app.ui.views.worker_history import render_worker_history_view
from app.ui.views.civic_intelligence import render_civic_intelligence

# Initialize SQLite/PostgreSQL Database
init_db()

st.set_page_config(
    page_title="FloodGuard | Pune Municipal Corporation",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(get_floodguard_css(), unsafe_allow_html=True)

# -------------------------------------------------------------
# Authentication Guard: Prompt sign-in if unauthenticated
# -------------------------------------------------------------
if not st.session_state.get("authenticated", False):
    render_login_page()
    st.stop()

user_role = st.session_state.get("role", "admin")

# -------------------------------------------------------------
# Role-based Routing: Worker Application vs Admin Console
# -------------------------------------------------------------
if user_role == "worker":
    WORKER_PAGE_SPECS = [
        ("worker-tasks", "My Tasks", ":material/checklist:",
         "Assigned drainage and hazard tasks", render_worker_tasks_view),
        ("worker-task-detail", "Task Detail", ":material/assignment:",
         "View hazard details and submit photo proof", render_worker_task_detail_view),
        ("worker-history", "Work History", ":material/history:",
         "Archive of completed and AI-verified tasks", render_worker_history_view),
    ]

    worker_pages = {
        slug: st.Page(fn, title=title, url_path=slug, default=(slug == "worker-tasks"))
        for slug, title, _ico, _desc, fn in WORKER_PAGE_SPECS
    }

    current = st.navigation(list(worker_pages.values()), position="hidden")
    current_slug = next((s for s, p in worker_pages.items() if p.url_path == current.url_path), "worker-tasks")

    # Handle programmatic navigation (e.g. from task card click)
    target_page = st.session_state.pop("active_worker_page", None)
    if target_page and target_page in worker_pages:
        st.switch_page(worker_pages[target_page])

    worker_name = st.session_state.get("worker_name", "Field Worker")
    worker_zone = st.session_state.get("worker_zone", "Pune")

    with st.container(key="fg_topnav"):
        cols = st.columns([2.8, 1.2, 1.3, 2.3, 1.1], vertical_alignment="center", gap="small")
        cols[0].markdown(
            f'''<div class="fg-nav-brand"><div class="fg-sb-logo">{BRAND_MARK}</div>
            <div><div class="fg-nav-title">FloodGuard Field</div><div class="fg-nav-org">PMC &bull; {worker_zone} Zone</div></div></div>''',
            unsafe_allow_html=True,
        )
        with cols[1].container(key=f"fgnav_{'active' if current_slug == 'worker-tasks' else 'idle'}_wtasks"):
            st.page_link(worker_pages["worker-tasks"], label="My Tasks", icon=":material/checklist:")
        with cols[2].container(key=f"fgnav_{'active' if current_slug == 'worker-history' else 'idle'}_whist"):
            st.page_link(worker_pages["worker-history"], label="Work History", icon=":material/history:")
        cols[3].markdown(
            f'''<div class="fg-nav-status"><span class="fg-top-dot"></span>
            <span class="fg-nav-clock">{datetime.now():%d %b &middot; %H:%M} IST</span>
            <span class="fg-nav-user-pill">👷 {worker_name}</span></div>''',
            unsafe_allow_html=True,
        )
        with cols[4].container(key="fg_logout_btn"):
            if st.button("Sign out", key="btn_worker_signout", icon=":material/logout:", use_container_width=True, help="Sign out of FloodGuard field app"):
                st.session_state.clear()
                st.rerun()

    current.run()

else:
    # -------------------------------------------------------------
    # Admin Console Routing
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
        ("civic-intel", "Civic Intel", ":material/public:",
         "Live Pune flood advisories, road closures, and citizen web complaints via TinyFish Web Search", render_civic_intelligence),
    ]

    pages = {
        slug: st.Page(fn, title=title, url_path=slug, default=(slug == "overview"))
        for slug, title, _ico, _desc, fn in PAGE_SPECS
    }
    current = st.navigation(list(pages.values()), position="hidden")
    current_slug = next((s for s, p in pages.items() if p.url_path == current.url_path), "overview")

    # Top navigation bar (Authenticated Admin Session)
    NAV_LABELS = {
        "overview": "Dashboard",
        "risk-map": "Risk Map",
        "cctv": "CCTV",
        "queue": "Queue",
        "analytics": "Analytics",
        "civic-intel": "Civic Intel",
    }
    user_email = st.session_state.get("auth_user", "admin@pune.gov.in")

    with st.container(key="fg_topnav"):
        cols = st.columns([2.2] + [1] * len(PAGE_SPECS) + [1.8, 1.1], vertical_alignment="center", gap="small")
        cols[0].markdown(
            f'''<div class="fg-nav-brand"><div class="fg-sb-logo">{BRAND_MARK}</div>
            <div><div class="fg-nav-title">FloodGuard</div><div class="fg-nav-org">Pune Municipal Corporation</div></div></div>''',
            unsafe_allow_html=True,
        )
        for col, (slug, title, ico, desc, _fn) in zip(cols[1:], PAGE_SPECS):
            label = NAV_LABELS.get(slug, title)
            state = "active" if slug == current_slug else "idle"
            with col.container(key=f"fgnav_{state}_{slug.replace('-', '_')}"):
                st.page_link(pages[slug], label=label, icon=ico, help=desc)
        cols[-2].markdown(
            f'''<div class="fg-nav-status"><span class="fg-top-dot"></span>
            <span class="fg-nav-clock">{datetime.now():%d %b &middot; %H:%M} IST</span>
            <span class="fg-nav-user-pill">{user_email}</span></div>''',
            unsafe_allow_html=True,
        )
        with cols[-1].container(key="fg_logout_btn"):
            if st.button("Sign out", key="btn_signout", icon=":material/logout:", use_container_width=True, help="Sign out of FloodGuard console"):
                st.session_state.clear()
                st.rerun()

    current.run()
