"""Detailed Site Investigation & Problem Diagnostic Report for clicked map hotspots."""

import textwrap
from html import escape
import streamlit as st
from typing import Dict, Any
from app.db.session import SessionLocal
from app.db.models import AuditLog
from app.ui.components.styles import INK, chip, status_color, status_pill

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
    t_pct = loc.get("traffic_congestion_pct", 35)
    t_speed = loc.get("traffic_speed_kmh", 25.0)
    t_level = loc.get("traffic_level", "Moderate Flow")
    is_busiest = loc.get("is_busiest_traffic", False)

    if is_busiest or t_pct >= 75:
        traffic_adv = f"Severe congestion: {t_pct}% ({t_speed} km/h). Police diversion recommended."
    elif t_pct >= 50:
        traffic_adv = f"Heavy congestion: {t_pct}% ({t_speed} km/h). Caution advisory for two-wheelers and heavy vehicles."
    elif t_pct >= 25:
        traffic_adv = f"Moderate traffic: {t_pct}% congestion ({t_speed} km/h)."
    else:
        traffic_adv = f"Free flow: {t_pct}% congestion ({t_speed} km/h)."

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
    """Render the site report card for the selected location."""
    diag = get_location_diagnostic_data(loc)
    r_level = loc["risk_level"]
    is_busiest = loc.get("is_busiest_traffic", False)
    t_pct = loc.get("traffic_congestion_pct", 40)
    t_speed = loc.get("traffic_speed_kmh", 25.0)
    t_delay = loc.get("traffic_delay_sec", 60)
    comp_score = loc.get("composite_score", loc["risk_score"])
    level_color = status_color(r_level)

    busiest_chip = chip("Heaviest traffic in Pune right now", "warn") if is_busiest else ""
    tags = "".join(chip(escape(t)) for t in diag["ai_tags"])

    def metric(label, value, note, color=INK):
        return (
            f'<div><div class="fg-k">{label}</div>'
            f'<div class="fg-mono" style="font-size:22px;font-weight:500;color:{color};margin:4px 0 2px 0;">{value}</div>'
            f'<div style="font-size:11.5px;color:#64708A;">{note}</div></div>'
        )

    metrics = "".join([
        metric("Conduit saturation", f"{loc['water_level_pct']}%", f"Standing depth {diag['depth_cm']} cm", level_color),
        metric("Rainfall", f"{loc.get('precip_mm', loc['rainfall_3h'])} mm", f"Chance of rain {loc.get('rain_chance_pct', 45)}%"),
        metric("Traffic congestion", f"{t_pct}%", f"{t_speed} km/h, +{t_delay}s delay",
               status_color("Critical") if t_pct >= 75 else INK),
        metric("Blockage", f"{loc['blockage_pct']}%", "Intake chamber", level_color),
        metric("Priority", f"#{loc.get('priority_rank', '-')}", f"Composite {comp_score}/100"),
    ])

    html = f"""
<div id="diagnostic-report-box" class="fg-card" style="border-color:{level_color}55; box-shadow: 0 0 0 3px {level_color}0F, var(--fg-shadow); margin:18px 0 10px 0; padding:18px 20px;">
  <div style="display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; align-items:flex-start; margin-bottom:14px;">
    <div style="min-width:0;">
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:8px;">
        {status_pill(r_level, f"{r_level} &middot; score {comp_score}")}
        {busiest_chip}
        <span class="fg-mono" style="font-size:11px; color:#64708A;">{loc['id']} &middot; updated {loc['last_updated']}</span>
      </div>
      <h3 class="fg-h3" style="font-size:19px !important;">{escape(loc['name'])}</h3>
      <div style="font-size:12.5px; color:#64708A; margin-top:3px;">
        Ward {loc['ward']} &middot; {loc['zone']} zone &middot; <span class="fg-mono">{loc['lat']}, {loc['lng']}</span> &middot; {loc['drain_type']}
      </div>
    </div>
  </div>
  <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:14px 18px; padding:14px 0; border-top:1px solid #EEF1F5; border-bottom:1px solid #EEF1F5;">
    {metrics}
  </div>
  <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:14px 24px; padding-top:14px;">
    <div><div class="fg-k">Assessment</div><div class="fg-v" style="margin-top:4px;">{escape(diag['problem_title'])}</div>
      <p style="font-size:12.5px; margin:4px 0 0 0; line-height:1.5;">{escape(diag['failure_mech'])}</p></div>
    <div><div class="fg-k">Recommended action</div><div class="fg-v" style="margin-top:4px;">{escape(diag['action_plan'])}</div>
      <p style="font-size:12.5px; margin:4px 0 0 0;">Expected to recede: {escape(diag['recede_eta'])}</p>
      <p style="font-size:12.5px; margin:2px 0 0 0;">Traffic: {escape(diag['traffic_adv'])}</p></div>
  </div>
  <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:12px;">{tags}</div>
</div>
"""
    st.markdown(" ".join(l.strip() for l in html.splitlines() if l.strip()), unsafe_allow_html=True)

    btn_col, _ = st.columns([1.4, 6.6])
    with btn_col:
        if st.button("Close report", key=f"close_{loc['id']}", use_container_width=True):
            st.session_state["selected_location_id"] = None
            st.session_state["last_handled_map_click"] = None
            if hasattr(st, "query_params") and "inspect" in st.query_params:
                try:
                    del st.query_params["inspect"]
                except Exception:
                    pass
            st.rerun()
