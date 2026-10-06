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
from app.ui.views.priority_queue import render_priority_queue
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
        "📹 CCTV Monitoring (6)",
        "⚠️ Priority Queue (3)",
        "🚜 Interventions",
        "📈 Flood Analytics"
    ]

    selected_nav = st.radio(
        "Navigation Menu",
        nav_options,
        index=0,
        label_visibility="collapsed"
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
# VIEW ROUTING
# -------------------------------------------------------------
if selected_nav == "📊 Dashboard":
    render_overview_dashboard()

elif selected_nav == "📍 Live Risk Map":
    render_live_risk_map()

elif selected_nav == "📹 CCTV Monitoring (6)":
    render_cctv_monitoring()

elif selected_nav == "⚠️ Priority Queue (3)":
    render_priority_queue()

elif selected_nav == "🚜 Interventions":
    render_interventions()

elif selected_nav == "📈 Flood Analytics":
    render_flood_analytics()
