"""Operations & Interventions View - Municipal Machinery & Crew Dispatch Tracker."""

import streamlit as st
from app.ui.pune_data import OPERATIONS_INTERVENTIONS

def render_interventions():
    """Render municipal interventions and machinery dispatch tracker."""

    st.markdown("""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>Municipal Operations & Interventions</h1>
            <p>Dewatering pumps, suction tankers, robotic rovers, and rapid response units</p>
        </div>
        <div class="header-actions">
            <div class="date-badge">🚜 4 Active Machinery Operations</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Dewatering Pumps", "6 Units", "+2 Deployed")
    m2.metric("Water Discharged", "2,270 m³", "↑ 180 m³/h")
    m3.metric("Suction Tankers En Route", "3 Units", "ETA < 15m")
    m4.metric("Avg Clearance Time", "48 mins", "↓ 12 mins")

    st.write("")

    # Active Operations Grid
    st.markdown("### 🚜 Real-Time Field Deployments")

    for op in OPERATIONS_INTERVENTIONS:
        status_color = "#16A34A" if "Operating" in op["status"] or "Deployed" in op["status"] else "#EA580C"

        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:16px 20px; margin-bottom:14px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <b style="font-size:15px; color:#0F172A;">{op['type']}</b>
                    <span style="font-size:12px; color:#64748B;">({op['id']})</span>
                </div>
                <span style="background:{status_color}15; color:{status_color}; font-weight:700; font-size:11px; padding:3px 10px; border-radius:12px; border:1px solid {status_color}40;">
                    {op['status']}
                </span>
            </div>

            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px; font-size:12px; color:#475569; padding-top:8px; border-top:1px solid #F1F5F9;">
                <div>📍 <b>Target Location:</b> {op['location']}</div>
                <div>👷 <b>Unit Lead:</b> {op['crew_head']}</div>
                <div>💧 <b>Water Pumped:</b> {op['water_discharged_m3']} m³</div>
                <div>⏱️ <b>ETA Resolution:</b> {op['eta_cleared']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Dispatch New Unit Form
    with st.expander("➕ Dispatch Additional Intervention Machinery / Emergency Crew"):
        f1, f2 = st.columns(2)
        with f1:
            eq_type = st.selectbox("Machinery Type", [
                "Mobile 500 GPM Dewatering Pump",
                "Mobile 1000 GPM Heavy Surcharge Pump",
                "High Pressure Silt Jetting & Suction Tanker",
                "Robotic Drain Cleaning Crawler",
                "Traffic Diversion Barricade Unit"
            ])
            target_loc = st.text_input("Target Location / Intersection", value="MG Road Junction")
        with f2:
            crew_head = st.text_input("Assigned Junior Engineer / Lead", value="S. Patil (Junior Engineer)")
            priority = st.selectbox("Deployment Priority", ["Emergency Priority 1 (Within 10m)", "Priority 2 (Within 30m)", "Routine Preventive"])

        if st.button("🚀 Confirm Deployment Order", type="primary"):
            st.success(f"Deployment Order dispatched for {eq_type} to {target_loc}! Crew alerted via SMS & Municipal Radio.")
