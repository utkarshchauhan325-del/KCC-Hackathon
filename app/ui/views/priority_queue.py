"""Priority queue: officer review of violations, open incidents and crew dispatch."""

import time
import textwrap
from html import escape
import streamlit as st
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import joinedload
from app.ui.pune_data import PRIORITY_QUEUE, PUNE_LOCATIONS, OPERATIONS_INTERVENTIONS
from app.db.session import SessionLocal
from app.db.models import Violation, Incident, Job, AuditLog
from app.notify.alerts import send_incident_alert
from app.ui.components.styles import _flat, page_header, section_title, status_pill
from app.ui.components.styles import status_color as _level_color
from app.ui.components.crew_dispatch import (
    render_crew_dispatch_widget,
    init_operations_state,
    get_available_leads,
    PUNE_MUNICIPAL_CREW_ROSTER,
)

# Municipal roster of Junior Engineers and Rapid Response Unit Leads across Pune
PUNE_MUNICIPAL_CREW_ROSTER = [
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

VIOLATION_EVIDENCE_LABELS = {
    "frame": "Scene (bystanders blurred)",
    "crop_person": "Person",
    "crop_vehicle": "Vehicle",
    "crop_plate": "Number plate",
}


def _review_violation(violation_id: str, decision: str, officer: str):
    """Record an officer's decision; approved violations are sent to the municipality.

    Returns the AlertLog rows for approvals (empty when no channel is configured).
    """
    db = SessionLocal()
    try:
        violation = db.query(Violation).filter(Violation.id == violation_id).first()
        if violation is None or violation.review_status != "pending_review":
            return []
        violation.review_status = decision
        violation.reviewed_by = officer
        violation.reviewed_at = datetime.utcnow()
        violation.incident.status = "acknowledged" if decision == "approved" else "rejected"
        db.add(AuditLog(user=officer, action=f"{decision}_violation", entity="violation", entity_id=violation.id))
        db.commit()
        if decision != "approved":
            return []
        return [(log.channel, log.status, log.response) for log in send_incident_alert(db, violation.incident)]
    finally:
        db.close()


def render_violation_review():
    """Officer review of AI-detected dumping violations from uploaded videos."""
    st.markdown(section_title(
        "Dumping violations awaiting review",
        "Detected in analysed CCTV video. Nothing is sent to the municipality until an officer approves it.",
    ), unsafe_allow_html=True)

    result = st.session_state.pop("violation_review_result", None)
    if result:
        decision, channels = result
        if decision == "rejected":
            st.info("Violation rejected. No evidence was sent.")
        elif not channels:
            st.warning("Violation approved, but no alert channel is configured (SMTP / Telegram / webhook in `.env`), so nothing was sent.")
        else:
            for channel, status, response in channels:
                (st.success if status == "sent" else st.error)(f"{channel}: {status} — {response}")

    db = SessionLocal()
    try:
        pending = (
            db.query(Violation)
            .options(joinedload(Violation.incident).joinedload(Incident.evidences), joinedload(Violation.incident).joinedload(Incident.job))
            .join(Violation.incident).join(Incident.job)
            .filter(Violation.review_status == "pending_review")
            .order_by(Job.created_at.desc())
            .all()
        )

        if not pending:
            st.caption("No pending violations. Violations appear here after a video is analysed with pass B enabled on the CCTV analysis page.")
            return

        st.caption(
            "Evidence is sent to the municipal corporation only after you approve it. "
            "Check that the person is clearly dumping waste and that the plate matches the vehicle before approving."
        )
        officer = st.text_input("Reviewing officer name", value=st.session_state.get("reviewing_officer", ""), key="reviewing_officer")

        for v in pending:
            inc = v.incident
            with st.container(border=True):
                st.markdown(f"**{inc.description}**")
                plate = v.plate_text or "not legible"
                plate_note = "" if not v.plate_text else (", valid format" if v.plate_valid else ", unusual format: verify manually")
                st.markdown(
                    f'<div class="fg-kv" style="border-top:none;padding-top:0;margin-bottom:8px;">'
                    f'<div><span class="fg-k">Video</span><span class="fg-v mono">{escape(inc.job.filename if inc.job else "?")} @ {inc.video_ts}</span></div>'
                    f'<div><span class="fg-k">Vehicle</span><span class="fg-v">{escape(v.vehicle_type or "On foot / none")}</span></div>'
                    f'<div><span class="fg-k">Plate</span><span class="fg-v mono">{escape(plate)}</span>'
                    f'<span style="font-size:11.5px;color:#64708A;">{escape(str(v.plate_legibility))}{plate_note}</span></div>'
                    f'<div><span class="fg-k">Model confidence</span><span class="fg-v mono">{inc.confidence:.0%}</span></div></div>',
                    unsafe_allow_html=True,
                )
                images = [(ev.kind, ev.path) for ev in inc.evidences if ev.kind in VIOLATION_EVIDENCE_LABELS and Path(ev.path).is_file()]
                images.sort(key=lambda kp: list(VIOLATION_EVIDENCE_LABELS).index(kp[0]))
                if images:
                    cols = st.columns(len(images))
                    for col, (kind, path) in zip(cols, images):
                        col.image(path, caption=VIOLATION_EVIDENCE_LABELS[kind], use_container_width=True)
                else:
                    st.warning("No evidence images were saved for this violation.")

                a, r, _ = st.columns([1.4, 1, 3])
                if a.button("Approve and send to PMC", key=f"approve_{v.id}", type="primary", disabled=not officer.strip()):
                    channels = _review_violation(v.id, "approved", officer.strip())
                    st.session_state["violation_review_result"] = ("approved", channels)
                    st.rerun()
                if r.button("Reject", key=f"reject_{v.id}", disabled=not officer.strip()):
                    _review_violation(v.id, "rejected", officer.strip())
                    st.session_state["violation_review_result"] = ("rejected", [])
                    st.rerun()
    finally:
        db.close()

    st.markdown("<hr class='fg-rule'>", unsafe_allow_html=True)


def render_priority_queue_and_interventions():
    """Render unified Priority Queue & Field Interventions Command Center.
    
    Directly attaches the 4 dispatch dropdowns under each hotspot requiring attention.
    When a crew is dispatched, displays the deployed machinery and the leader's name under that section.
    """

    # Initialize session state for persistent operations
    if "operations_list" not in st.session_state:
        st.session_state["operations_list"] = [dict(op) for op in OPERATIONS_INTERVENTIONS]

    operations = st.session_state["operations_list"]

    # Calculate active deployed locations and leads for dynamic filtering
    deployed_locations_raw = [op["location"].strip().lower() for op in operations]
    deployed_leads_raw = [op["crew_head"].strip().lower() for op in operations]

    # Filter locations: ONLY show places which are NOT yet under command
    available_locations = []
    for loc in PUNE_LOCATIONS:
        loc_name = loc["name"].strip()
        loc_lower = loc_name.lower()
        is_deployed = any(
            loc_lower == dep or loc_lower in dep or dep in loc_lower
            for dep in deployed_locations_raw
        )
        if not is_deployed:
            available_locations.append(loc_name)

    # Filter crew leads: ONLY show officers who are currently open / available
    available_leads = [
        lead for lead in PUNE_MUNICIPAL_CREW_ROSTER
        if lead.strip().lower() not in deployed_leads_raw
    ]

    # Dynamic metrics
    pump_count = sum(op.get("units", 1) for op in operations if "Pump" in op.get("type", ""))
    total_water = sum(op.get("water_discharged_m3", 0) for op in operations)
    en_route_count = sum(1 for op in operations if "En Route" in op.get("status", ""))

    st.markdown(page_header(
        "Priority queue",
        "Review detected violations, then assign machinery and an available engineer to each open incident.",
        eyebrow="Operations",
        meta=[f"<b>{len(PRIORITY_QUEUE)}</b> open incidents", f"<b>{len(operations)}</b> crews deployed",
              f"<b>{len(available_leads)}</b> engineers available"],
    ), unsafe_allow_html=True)

    toast_data = st.session_state.pop("deploy_success_data", None)
    if toast_data:
        st.toast(f"{toast_data['id']}: {toast_data['eq_type']} dispatched to {toast_data['target_loc']} (lead: {toast_data['crew_head']})")

    render_violation_review()

    st.markdown(section_title(
        "Open incidents",
        "Highest severity first. Choose machinery and an available engineer to dispatch a crew.",
    ), unsafe_allow_html=True)

    # Iterate through Priority Queue locations requiring attention
    for i, item in enumerate(PRIORITY_QUEUE):
        loc_name = item["location"]
        loc_lower = loc_name.strip().lower()

        # Check if a crew is currently deployed for this specific place
        deployed_op = None
        for op in operations:
            dep_loc_lower = op.get("location", "").strip().lower()
            if loc_lower == dep_loc_lower:
                deployed_op = op
                break

        # Incident card
        sev_level = "Critical" if item["severity"] >= 5 else "High"
        plate_html = (
            f'<div><span class="fg-k">Detected plate</span><span class="fg-v mono">{item["plate_text"]}</span></div>'
            if "plate_text" in item else ""
        )
        st.markdown(_flat(f"""
        <div class="fg-card" style="margin-bottom:8px; box-shadow: inset 3px 0 0 {_level_color(sev_level)}, var(--fg-shadow);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px; flex-wrap:wrap; margin-bottom:8px;">
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    {status_pill(sev_level, f"Severity {item['severity']}/5")}
                    <span style="font-family:var(--fg-font-head); font-size:16px; font-weight:600; color:#0B1220;">{item['location']}</span>
                    <span style="font-size:12px; color:#64708A;">{item['zone']} zone</span>
                </div>
                <div class="fg-mono" style="font-size:11px; color:#94A0B4;">{item['id']} &middot; reported {item['reported_at']}</div>
            </div>
            <p style="font-size:13.5px; line-height:1.55; margin:0 0 12px 0;">{item['description']}</p>
            <div class="fg-kv">
                <div><span class="fg-k">Category</span><span class="fg-v">{item['category']}</span></div>
                <div><span class="fg-k">Risk score</span><span class="fg-v mono">{item['risk_score']}/100</span></div>
                <div><span class="fg-k">Suggested action</span><span class="fg-v">{item['suggested_action']}</span></div>
                {plate_html}
            </div>
        </div>
        """), unsafe_allow_html=True)

        # UNDER EACH PLACE: Unified crew dispatch & intervention widget
        sugg_mach = (
            "High Pressure Silt Jetting & Suction Tanker"
            if "Jetting" in item.get("suggested_action", "")
            else "Mobile 500 GPM Dewatering Pump"
        )
        render_crew_dispatch_widget(
            location_name=item["location"],
            key_prefix=f"pq_{item['id']}",
            suggested_machinery=sugg_mach,
            zone=item["zone"],
            incident_id=item["id"],
            header_title=None,
        )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # OTHER ACTIVE MUNICIPAL OPERATIONS ACROSS PUNE
    # -------------------------------------------------------------
    other_ops = [
        op for op in operations
        if not any(op.get("location", "").strip().lower() == item["location"].strip().lower() for item in PRIORITY_QUEUE)
    ]

    if other_ops:
        st.markdown(section_title("Other active deployments", "Crews working at locations outside the open-incident list."), unsafe_allow_html=True)
        for idx, op in enumerate(other_ops):
            status_color = "#16A34A" if "Operating" in op["status"] or "Deployed" in op["status"] else "#EA580C"
            card_col, btn_col = st.columns([5.2, 1], gap="small")
            with card_col:
                op_html = _flat(f"""
                <div class="fg-card" style="margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
                        <div style="display:flex; align-items:center; gap:10px;">
                            <span style="font-size:14px; font-weight:600; color:#0B1220;">{op['type']}</span>
                            <span class="fg-mono" style="font-size:11px; color:#64708A;">{op['id']}</span>
                        </div>
                        <span style="font-size:12px; color:#334155;">{op['status']}</span>
                    </div>
                    <div class="fg-kv">
                        <div><span class="fg-k">Location</span><span class="fg-v">{op['location']}</span></div>
                        <div><span class="fg-k">Unit lead</span><span class="fg-v">{op['crew_head']}</span></div>
                        <div><span class="fg-k">Water pumped</span><span class="fg-v mono">{op.get('water_discharged_m3', 0)} m&sup3;</span></div>
                        <div><span class="fg-k">Expected clear</span><span class="fg-v">{op.get('eta_cleared', '-')}</span></div>
                    </div>
                </div>
                """)
                st.markdown(op_html, unsafe_allow_html=True)
            with btn_col:
                st.write("")
                if st.button("Recall crew", key=f"demob_other_{op['id']}_{idx}", help=f"Recall crew from {op['location']} and return officer to pool", use_container_width=True):
                    operations.remove(op)
                    st.session_state["operations_list"] = operations
                    st.rerun()

    # Expander to dispatch additional machinery to any other hotspot in Pune
    with st.expander("Dispatch a crew to another location"):
        f1, f2 = st.columns(2)
        with f1:
            gen_eq_type = st.selectbox(
                "Machinery",
                [
                    "High Pressure Silt Jetting & Suction Tanker",
                    "Mobile 500 GPM Dewatering Pump",
                    "Mobile 1000 GPM Heavy Surcharge Pump",
                    "Robotic Drain Cleaning Crawler",
                    "Traffic Diversion Barricade Unit"
                ],
                key="gen_eq_type"
            )

            if available_locations:
                gen_target_loc = st.selectbox(
                    "Location (unassigned only)",
                    available_locations,
                    key="gen_target_loc"
                )
            else:
                st.warning("Every listed location already has a crew assigned.")
                gen_target_loc = None

        with f2:
            if available_leads:
                gen_crew_head = st.selectbox(
                    "Assigned engineer (available only)",
                    available_leads,
                    key="gen_crew_head"
                )
            else:
                st.warning("All engineers are currently deployed.")
                gen_crew_head = None

            gen_priority = st.selectbox(
                "Priority",
                [
                    "Priority 1 (within 10 min)",
                    "Priority 2 (within 30 min)",
                    "Routine Preventive"
                ],
                key="gen_priority"
            )

        gen_can_deploy = bool(gen_target_loc and gen_crew_head)
        if st.button("Dispatch crew", key="gen_deploy_btn", type="primary", disabled=not gen_can_deploy):
            new_id = f"OP-{700 + len(operations) + 1}"
            eta = "20 mins" if "10 min" in gen_priority else ("45 mins" if "30 min" in gen_priority else "1h 30m")
            new_op = {
                "id": new_id,
                "type": gen_eq_type,
                "location": gen_target_loc,
                "status": "Deployed & En Route",
                "crew_head": gen_crew_head,
                "units": 1,
                "water_discharged_m3": 0,
                "eta_cleared": eta
            }
            st.session_state["operations_list"].insert(0, new_op)
            st.session_state["deploy_success_data"] = {
                "id": new_id,
                "eq_type": gen_eq_type,
                "target_loc": gen_target_loc,
                "crew_head": gen_crew_head,
                "priority": gen_priority,
                "timestamp": time.time()
            }
            st.rerun()

def render_priority_queue():
    """Alias for unified view."""
    render_priority_queue_and_interventions()
