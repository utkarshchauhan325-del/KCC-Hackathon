"""FloodGuard - Municipal Intelligence Web Application.

Real-time flood risk monitoring, early warning system, and CCTV AI inspection.
"""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
from app.config import settings
from app.db.session import init_db
from app.ui.components.styles import get_floodguard_css
from app.ui.views.overview import render_overview_dashboard
from app.ui.views.live_map import render_live_risk_map
from app.ui.views.cctv_monitoring import render_cctv_monitoring
from app.ui.views.priority_queue import render_priority_queue, render_priority_queue_and_interventions
from app.ui.views.interventions import render_interventions
from app.ui.views.flood_analytics import render_flood_analytics

# Initialize SQLite/PostgreSQL Database
init_db()

# Streamlit Page Config
st.set_page_config(
    page_title="FloodGuard - Municipal Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom FloodGuard CSS theme
st.markdown(get_floodguard_css(), unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR NAVIGATION - MATCHING SCREENSHOT PRECISELY
# -------------------------------------------------------------
import textwrap

with st.sidebar:
    # FloodGuard Brand Header
    st.markdown(textwrap.dedent("""
    <div class="brand-container">
        <div style="background:#0284C7; width:34px; height:34px; border-radius:8px; display:flex; align-items:center; justify-content:center; color:white; font-size:18px;">
            🌊
        </div>
        <div>
            <div class="brand-title">FloodGuard</div>
            <div class="brand-sub">Municipal Intelligence</div>
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

    # Navigation options
    nav_options = [
        "📊 Dashboard",
        "📍 Live Risk Map",
        "📹 CCTV Surveillance (6)",
        "⚠️ Priority Queue & Interventions (3)",
        "📈 Flood Analytics"
    ]

    if "nav_selection" not in st.session_state or st.session_state["nav_selection"] not in nav_options:
        st.session_state["nav_selection"] = "📊 Dashboard"

    def on_sidebar_nav_change():
        st.session_state["nav_selection"] = st.session_state["sidebar_nav_radio"]

    curr_idx = nav_options.index(st.session_state["nav_selection"]) if st.session_state["nav_selection"] in nav_options else 0

    st.radio(
        "Navigation Menu",
        nav_options,
        index=curr_idx,
        label_visibility="collapsed",
        key="sidebar_nav_radio",
        on_change=on_sidebar_nav_change
    )

    # Bottom Municipal Organization Tag
    st.markdown(textwrap.dedent("""
    <div class="municipal-footer">
        <div style="font-size:20px;">🏛️</div>
        <div>
            <p class="footer-title">Pune Municipal Corp.</p>
            <p class="footer-sub">Zone: Central</p>
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

# -------------------------------------------------------------
# TOP NAVIGATION STRIP (Always visible even if sidebar is collapsed)
# -------------------------------------------------------------
st.markdown(textwrap.dedent("""
<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:10px 16px; margin-bottom:14px; box-shadow:0 1px 3px rgba(0,0,0,0.03); display:flex; justify-content:space-between; align-items:center;">
    <div style="display:flex; align-items:center; gap:10px;">
        <span style="background:#0284C7; color:white; font-size:14px; width:26px; height:26px; border-radius:6px; display:inline-flex; align-items:center; justify-content:center;">🌊</span>
        <span style="font-weight:800; font-size:14px; color:#0F172A; letter-spacing:-0.01em;">FloodGuard Intelligence Portal</span>
        <span style="background:#E0F2FE; color:#0284C7; font-size:10px; font-weight:700; padding:2px 8px; border-radius:12px; border:1px solid #BAE6FD;">LIVE MUNICIPAL FEED</span>
    </div>
    <div style="display:flex; align-items:center; gap:14px; font-size:12px; color:#64748B;">
        <span>🏛️ <b>PMC</b> Pune Central Command</span>
        <span>🟢 <b>Online</b></span>
    </div>
</div>
""").strip(), unsafe_allow_html=True)

nav_cols = st.columns([1.1, 1.25, 1.6, 2.0, 1.25])
for i, opt in enumerate(nav_options):
    with nav_cols[i]:
        is_active = (st.session_state["nav_selection"] == opt)
        btn_type = "primary" if is_active else "secondary"
        if st.button(opt, key=f"top_nav_{i}", type=btn_type, use_container_width=True):
            st.session_state["nav_selection"] = opt
            st.rerun()

current_view = st.session_state["nav_selection"]

# -------------------------------------------------------------
# VIEW ROUTING
# -------------------------------------------------------------
if current_view == "📊 Dashboard":
    render_overview_dashboard()

elif current_view == "📍 Live Risk Map":
    render_live_risk_map()

elif "CCTV" in current_view:
    render_cctv_monitoring()

elif "Priority Queue" in current_view or "Intervention" in current_view:
    render_priority_queue_and_interventions()

elif "Flood Analytics" in current_view or "Analytics" in current_view:
    render_flood_analytics()

