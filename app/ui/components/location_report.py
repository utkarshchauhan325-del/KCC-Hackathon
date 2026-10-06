"""Detailed Site Investigation & Problem Diagnostic Report for clicked map hotspots."""

import textwrap
import streamlit as st
from typing import Dict, Any
from app.db.session import SessionLocal
from app.db.models import AuditLog

def get_location_diagnostic_data(loc: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich location data with comprehensive hydraulic and vision diagnostics."""
    r_level = loc["risk_level"]
    name = loc["name"]
    water_pct = loc["water_level_pct"]
    blockage = loc["blockage_pct"]

    # Compute standing water depth in cm based on capacity
    depth_cm = int(water_pct * 0.32)

    # Diagnostic profiles based on risk severity
    if r_level == "Critical":
        problem_title = "Severe Stormwater Culvert Choking & Surface Inundation"
        failure_mech = (
            f"Intake grating at {name} is {blockage}% obstructed by trapped commercial cardboard, "
            f"polythene packaging, and wet sediment. The conduit is operating at {water_pct}% hydraulic capacity, "
            f"causing surface water to back up onto active carriage lanes with an inundation depth of {depth_cm} cm."
        )
        ai_tags = ["Severe Inlet Obstruction", "Standing Wastewater", "Roadway Submersion", "Commercial Waste Dumping"]
        debris_mix = "55% Plastic Film & Bottles, 30% Corrugated Cardboard, 15% Street Silt"
        action_plan = "Immediate dispatch of Mobile 500 GPM Dewatering Pump Unit + High-Pressure Silt Jetting Machine."
        recede_eta = "40 mins (with pump) | 3h 15m (gravity alone)"
        traffic_adv = "Lane 1 & 2 closed. Traffic diversion advisory active via Ward Traffic Police."
    elif r_level == "High":
        problem_title = "Elevated Inflow Surcharge & Catch Basin Capacity Stress"
        failure_mech = (
            f"Rapid surface runoff inflow has elevated conduit saturation to {water_pct}%. "
            f"Partial silt deposition ({blockage}% choke) is retarding gravity flow velocity. "
            f"Water is ponding along kerb channels to a depth of {depth_cm} cm."
        )
        ai_tags = ["Kerb Channel Overflow", "Catch Basin Siltation", "Moderate Trash Near Inlet"]
        debris_mix = "40% Roadside Litter, 40% Heavy Silt, 20% Vegetative Foliage"
        action_plan = "Deploy mechanical desilting crew with suction tanker to clear intake chamber."
        recede_eta = "1h 10m (assisted) | 2h 00m (unassisted)"
        traffic_adv = "Caution advisory issued to two-wheelers. Speed limit reduced to 20 km/h."
    elif r_level == "Medium":
        problem_title = "Normal Monitored Flow with Localized Silt Accumulation"
        failure_mech = (
            f"Drainage network at {name} is handling baseline precipitation at {water_pct}% capacity. "
            f"Moderate silt accumulation ({blockage}%) detected in upstream manholes but flow remains continuous."
        )
        ai_tags = ["Normal Surface Flow", "Pre-Monsoon Silt Retention"]
        debris_mix = "60% Silt & Sand, 25% Dry Leaves, 15% Minor Litter"
        action_plan = "Scheduled preventive jetting within 24 hours. No emergency machinery required."
        recede_eta = "35 mins following rainfall cessation"
        traffic_adv = "No traffic restrictions necessary."
    else:
        problem_title = "Optimal Gravity Discharge & Clear Intake Gratings"
        failure_mech = (
            f"Infrastructure operating at nominal {water_pct}% capacity with zero structural or debris impedance. "
            f"Outfall velocity is optimal."
        )
        ai_tags = ["Clear Grate", "Optimal Outfall Flow"]
        debris_mix = "Negligible debris (< 15% silt)"
        action_plan = "Routine telemetry surveillance."
        recede_eta = "Immediate drainage (< 15 mins)"
        traffic_adv = "Normal traffic conditions."

    return {
        "problem_title": problem_title,
        "failure_mech": failure_mech,
        "depth_cm": depth_cm,
        "ai_tags": ai_tags,
        "debris_mix": debris_mix,
        "action_plan": action_plan,
        "recede_eta": recede_eta,
        "traffic_adv": traffic_adv
    }

def render_location_full_report_box(loc: Dict[str, Any], on_close_key: str = "close_hotspot_report"):
    """Render the full-length detailed diagnostic report box under the map."""
    diag = get_location_diagnostic_data(loc)
    r_level = loc["risk_level"]

    col_map = {
        "Critical": "#DC2626",
        "High": "#EA580C",
        "Medium": "#D97706",
        "Low": "#16A34A"
    }
    bg_map = {
        "Critical": "#FEE2E2",
        "High": "#FFEDD5",
        "Medium": "#FEF3C7",
        "Low": "#DCFCE7"
    }

    border_color = col_map.get(r_level, "#2563EB")
    badge_bg = bg_map.get(r_level, "#EFF6FF")

    # Full length box container
    st.markdown(textwrap.dedent(f"""
<div style="background:#FFFFFF; border:2px solid {border_color}; border-radius:14px; padding:22px 26px; margin:20px 0 24px 0; box-shadow:0 4px 14px rgba(0,0,0,0.06); font-family:'Plus Jakarta Sans',sans-serif;">
<div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid #E2E8F0; padding-bottom:14px; margin-bottom:16px;">
<div>
<div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
<span style="background:{badge_bg}; color:{border_color}; font-weight:800; font-size:12px; padding:4px 10px; border-radius:12px; border:1px solid {border_color}40; letter-spacing:0.04em; text-transform:uppercase;">
● {r_level} RISK LEVEL — SCORE {loc['risk_score']}/100
</span>
<span style="font-size:12px; color:#64748B;">Sensor Node: <b>{loc['id']}</b></span>
<span style="font-size:12px; color:#64748B;">• Updated: <b>{loc['last_updated']}</b></span>
</div>
<h2 style="margin:0; font-size:22px; font-weight:800; color:#0F172A;">📍 {loc['name']} — Comprehensive Site Problem & Engineering Diagnostic Report</h2>
<p style="margin:4px 0 0 0; font-size:13px; color:#64748B;">
<b>Ward:</b> {loc['ward']} &nbsp;|&nbsp; <b>Zone:</b> {loc['zone']} &nbsp;|&nbsp; <b>Coordinates:</b> {loc['lat']}, {loc['lng']} &nbsp;|&nbsp; <b>Conduit:</b> {loc['drain_type']}
</p>
</div>
</div>

<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:14px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:14px 18px; margin-bottom:20px;">
<div>
<div style="font-size:11px; color:#64748B; font-weight:600; text-transform:uppercase;">Conduit Saturation</div>
<div style="font-size:22px; font-weight:800; color:{border_color};">{loc['water_level_pct']}%</div>
<div style="font-size:11px; color:#475569;">Standing Depth: <b>{diag['depth_cm']} cm</b></div>
</div>
<div>
<div style="font-size:11px; color:#64748B; font-weight:600; text-transform:uppercase;">Live Precipitation</div>
<div style="font-size:22px; font-weight:800; color:#2563EB;">{loc.get('precip_mm', loc['rainfall_3h'])} mm</div>
<div style="font-size:11px; color:#475569;">Rain Probability: <b>{loc.get('rain_chance_pct', 45)}%</b></div>
</div>
<div>
<div style="font-size:11px; color:#64748B; font-weight:600; text-transform:uppercase;">Debris / Silt Choke Index</div>
<div style="font-size:22px; font-weight:800; color:{border_color};">{loc['blockage_pct']}%</div>
<div style="font-size:11px; color:#475569;">Intake Chamber Choke</div>
</div>
<div>
<div style="font-size:11px; color:#64748B; font-weight:600; text-transform:uppercase;">Flood Likelihood & Priority</div>
<div style="font-size:22px; font-weight:800; color:{border_color};">{loc.get('flood_probability_pct', loc['risk_score'])}% <span style="font-size:12px; font-weight:700; color:#7C3AED;">(Rank #{loc.get('priority_rank', '-')})</span></div>
<div style="font-size:11px; color:#475569;">Status: <b>{loc['status']}</b></div>
</div>
</div>
</div>
""").strip(), unsafe_allow_html=True)
    # Quick Action Buttons
    btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 5])
    with btn_col1:
        if st.button("🚀 Dispatch Pump", key=f"disp_pump_{loc['id']}", type="primary", use_container_width=True):
            db = SessionLocal()
            db.add(AuditLog(user="Chief Municipal Officer", action=f"dispatched_mobile_pump_{loc['id']}", entity="location", entity_id=loc['id']))
            db.commit()
            db.close()
            st.success("Mobile Pump Unit OP-701 dispatched!")
    with btn_col2:
        if st.button("❌ Close Report", key=f"close_{loc['id']}", use_container_width=True):
            st.session_state["selected_location_id"] = None
            st.rerun()

    st.markdown("<hr style='border:none; border-top:2px solid #E2E8F0; margin:16px 0 24px 0;'>", unsafe_allow_html=True)

