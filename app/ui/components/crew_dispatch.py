"""Reusable municipal crew dispatch and field intervention widget for Pune Disaster Cell.

Enables 1-click tactical crew deployment and demobilization directly at the
incident detection site (CCTV / AI analysis) or in the Priority Queue.
Zero emojis, strict type safety, persistent session state across views.
"""

import time
from typing import Dict, List, Optional
import streamlit as st

from app.db.models import AuditLog
from app.db.session import SessionLocal
from app.ui.components.styles import _flat, status_color as _level_color, status_pill
from app.ui.pune_data import OPERATIONS_INTERVENTIONS, PUNE_LOCATIONS

# Municipal roster of Junior Engineers and Rapid Response Leads across Pune
PUNE_MUNICIPAL_CREW_ROSTER: List[str] = [
    "S. Patil (Junior Engineer)",
    "V. Kadam (Roads & Drainage)",
    "Traffic Ward 3",
    "Disaster Cell Engr. 2",
    "R. Deshmukh (Drainage Specialist - Shivajinagar)",
    "A. Shinde (Junior Engineer - Aundh)",
    "M. Joshi (Quick Response - Swargate)",
    "P. More (Mechanical Division - Hadapsar)",
    "K. Gaikwad (Disaster Mgmt - Kothrud)",
    "N. Kulkarni (River & Sluice Gate Engr)",
    "T. Pawar (Stormwater Ops - Bibwewadi)",
    "H. Salunke (Rapid Dewatering Crew)",
    "B. Jagtap (Suction Jetting Lead - Yerwada)",
    "C. Kamble (Culvert Maintenance - PCMC)",
    "D. Wagh (Hydraulic Emergency - Dapodi)",
]

MACHINERY_OPTIONS: List[str] = [
    "High Pressure Silt Jetting & Suction Tanker",
    "Mobile 500 GPM Dewatering Pump",
    "Mobile 1000 GPM Heavy Surcharge Pump",
    "Robotic Drain Cleaning Crawler",
    "Traffic Diversion Barricade Unit",
    "Solid Waste Rapid Clearance Unit",
]


def init_operations_state() -> List[Dict]:
    """Ensure persistent operations list is initialized in session state."""
    if "operations_list" not in st.session_state:
        st.session_state["operations_list"] = [dict(op) for op in OPERATIONS_INTERVENTIONS]
    return st.session_state["operations_list"]


def get_deployed_operation(loc_name: str) -> Optional[Dict]:
    """Check if an active municipal operation is assigned to this location."""
    operations = init_operations_state()
    loc_clean = loc_name.strip().lower()
    for op in operations:
        op_loc = op.get("location", "").strip().lower()
        if loc_clean == op_loc or loc_clean in op_loc or op_loc in loc_clean:
            return op
    return None


def get_available_leads() -> List[str]:
    """Return municipal engineers who are not currently on an active mission."""
    operations = init_operations_state()
    deployed_leads = {op.get("crew_head", "").strip().lower() for op in operations}
    return [lead for lead in PUNE_MUNICIPAL_CREW_ROSTER if lead.strip().lower() not in deployed_leads]


def render_crew_dispatch_widget(
    location_name: str,
    key_prefix: str,
    suggested_machinery: Optional[str] = None,
    zone: str = "Central",
    incident_id: Optional[str] = None,
    header_title: Optional[str] = "Crew deployment & field intervention",
) -> None:
    """Render unified crew deployment panel for a specific location.

    Shows active crew status and recall option if deployed;
    otherwise renders the machinery/engineer dispatch form.
    """
    operations = init_operations_state()
    deployed_op = get_deployed_operation(location_name)
    available_leads = get_available_leads()

    if header_title:
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin:16px 0 8px 0;">
                <span class="fg-k" style="font-size:12px; font-weight:700; letter-spacing:0.04em; text-transform:uppercase;">
                    {header_title} &middot; {location_name}
                </span>
                <span class="fg-mono" style="font-size:11px; color:#64748B;">
                    Zone: {zone}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if deployed_op:
        # ACTIVE CREW DEPLOYED FOR THIS SITE
        st.markdown(
            _flat(f"""
            <div class="fg-card" style="background:#F7FBF9; border-color:#CFE8DA; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
                    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                        {status_pill('Low', 'Crew deployed')}
                        <span style="font-size:14px; font-weight:600; color:#0B1220;">{deployed_op['type']}</span>
                        <span class="fg-mono" style="font-size:11px; color:#64708A;">{deployed_op['id']}</span>
                    </div>
                    <span style="font-size:12px; font-weight:500; color:#047857;">{deployed_op['status']}</span>
                </div>
                <div class="fg-kv" style="border-top-color:#DCEFE4;">
                    <div><span class="fg-k">Unit lead</span><span class="fg-v">{deployed_op['crew_head']}</span></div>
                    <div><span class="fg-k">Water pumped</span><span class="fg-v mono">{deployed_op.get('water_discharged_m3', 0)} m&sup3;</span></div>
                    <div><span class="fg-k">Expected clear</span><span class="fg-v">{deployed_op.get('eta_cleared', '30 mins')}</span></div>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

        demob_col1, demob_col2 = st.columns([5, 1.2])
        with demob_col2:
            if st.button("Recall crew", key=f"recall_{key_prefix}_{deployed_op['id']}", use_container_width=True):
                operations = [op for op in operations if op["id"] != deployed_op["id"]]
                st.session_state["operations_list"] = operations
                try:
                    db = SessionLocal()
                    db.add(AuditLog(
                        user="Chief Municipal Officer",
                        action=f"demobilized_{deployed_op['id']}_from_{location_name}",
                        entity="operation",
                        entity_id=deployed_op["id"]
                    ))
                    db.commit()
                    db.close()
                except Exception:
                    pass
                st.toast(f"Recalled {deployed_op['type']} from {location_name}")
                st.rerun()

    else:
        # NO CREW DEPLOYED: Show interactive dispatch controls
        with st.container(border=True):
            st.markdown(
                f"<div class='fg-k' style='margin-bottom:8px; font-weight:600; color:#0B1220;'>Dispatch tactical crew to {location_name}</div>",
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns(2)
            with col1:
                # Default machinery selection
                mach_idx = 0
                if suggested_machinery and suggested_machinery in MACHINERY_OPTIONS:
                    mach_idx = MACHINERY_OPTIONS.index(suggested_machinery)

                mach_type = st.selectbox(
                    "Machinery",
                    MACHINERY_OPTIONS,
                    index=mach_idx,
                    key=f"mach_{key_prefix}"
                )

                # Location options (defaults to target site, with all Pune locations available)
                all_loc_names = [l["name"] for l in PUNE_LOCATIONS]
                if location_name not in all_loc_names:
                    all_loc_names.insert(0, location_name)
                loc_idx = all_loc_names.index(location_name) if location_name in all_loc_names else 0

                target_loc = st.selectbox(
                    "Target location",
                    all_loc_names,
                    index=loc_idx,
                    key=f"loc_{key_prefix}",
                    help="Site where machinery will be dispatched"
                )

            with col2:
                if available_leads:
                    assigned_lead = st.selectbox(
                        "Assigned engineer (available only)",
                        available_leads,
                        key=f"lead_{key_prefix}",
                        help="Engineers currently on active duty are excluded"
                    )
                else:
                    st.warning("All engineers are currently deployed across Pune corridors.")
                    assigned_lead = None

                prio = st.selectbox(
                    "Response priority",
                    [
                        "Priority 1 (within 10 min)",
                        "Priority 2 (within 30 min)",
                        "Routine Preventive"
                    ],
                    key=f"prio_{key_prefix}"
                )

            can_deploy = bool(target_loc and assigned_lead)
            btn_label = f"Dispatch to {target_loc}"
            if st.button(
                btn_label,
                key=f"deploy_btn_{key_prefix}",
                type="primary",
                disabled=not can_deploy,
                use_container_width=False
            ):
                new_id = f"OP-{700 + len(operations) + 1}"
                eta = "20 mins" if "10 min" in prio else ("45 mins" if "30 min" in prio else "1h 30m")
                new_op = {
                    "id": new_id,
                    "type": mach_type,
                    "location": target_loc,
                    "status": "Deployed & En Route",
                    "crew_head": assigned_lead,
                    "units": 1,
                    "water_discharged_m3": 0,
                    "eta_cleared": eta
                }

                # Prepend to active operations list
                st.session_state["operations_list"].insert(0, new_op)

                # Toast message for feedback
                st.session_state["deploy_success_data"] = {
                    "id": new_id,
                    "eq_type": mach_type,
                    "target_loc": target_loc,
                    "crew_head": assigned_lead,
                    "priority": prio,
                    "timestamp": time.time()
                }

                # Audit log in database
                try:
                    db = SessionLocal()
                    db.add(AuditLog(
                        user="Chief Municipal Officer",
                        action=f"dispatched_{new_id}_{mach_type}_to_{target_loc}",
                        entity="operation",
                        entity_id=new_id,
                        details=f"Machinery: {mach_type} | Lead: {assigned_lead} | Priority: {prio}"
                    ))
                    db.commit()
                    db.close()
                except Exception:
                    pass

                st.toast(f"Dispatched {mach_type} to {target_loc} (Lead: {assigned_lead})")
                st.rerun()
