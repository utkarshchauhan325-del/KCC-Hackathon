"""Priority queue: open incidents with their evidence photos, officer review of violations, and crews."""

import json
import time
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
from sqlalchemy.orm import joinedload

from app.config import settings
from app.db.models import AuditLog, Incident, Job, Violation
from app.db.session import SessionLocal
from app.notify.alerts import send_incident_alert
from app.ui.components.crew_dispatch import (
    PUNE_MUNICIPAL_CREW_ROSTER,
    get_available_leads,
    init_operations_state,
    render_crew_dispatch_widget,
)
from app.ui.components.evidence_frames import incident_frame
from app.ui.components.styles import STATUS, _flat, icon, page_header, section_title, status_pill
from app.ui.pune_data import ASSIGNED_CAMERAS, PRIORITY_QUEUE, PUNE_LOCATIONS, location_for_job

VIOLATION_EVIDENCE_LABELS = {
    "frame": "Scene (bystanders blurred)",
    "crop_person": "Person",
    "crop_vehicle": "Vehicle",
    "crop_plate": "Number plate",
}

_ACTION_BY_TYPE = {
    "drainage": ("Clear the drain with silt jetting and suction", "High Pressure Silt Jetting & Suction Tanker"),
    "garbage": ("Remove the garbage and check for repeat dumping", "Solid Waste Rapid Clearance Unit"),
    "road": ("Barricade and repair the road surface", "Traffic Diversion Barricade Unit"),
}
_CATEGORY_BY_TYPE = {"drainage": "Drain blockage", "garbage": "Garbage and dumping", "road": "Road hazard"}


def _ago(ts: datetime) -> str:
    secs = max(0, (datetime.utcnow() - ts).total_seconds())
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} h ago"
    return f"{int(secs // 86400)} d ago"


def _job_score(job_id: str):
    try:
        return json.loads((settings.EVIDENCE_DIR / job_id / "result.json").read_text(encoding="utf-8")).get("composite_score")
    except (OSError, ValueError):
        return None


def _cctv_incidents(db) -> List[Dict[str, Any]]:
    """Open incidents found in analysed videos, newest analysis first.

    Re-analysing the same footage replaces its earlier incidents: only the latest
    finding of each kind per location is kept.
    """
    rows = (
        db.query(Incident)
        .options(joinedload(Incident.evidences), joinedload(Incident.job))
        .join(Incident.job)
        .filter(Incident.status == "new", Incident.subtype != "dumping_violation", Job.status == "completed")
        .order_by(Job.created_at.desc(), Incident.severity.desc())
        .all()
    )
    cam_by_loc = {c["location_id"]: c for c in ASSIGNED_CAMERAS}
    items, seen = [], set()
    for inc in rows:
        loc = location_for_job(inc.job.filename, inc.job.source_gps)
        if (loc["id"], inc.subtype) in seen:
            continue
        seen.add((loc["id"], inc.subtype))
        cam = cam_by_loc.get(loc["id"])
        action, machinery = _ACTION_BY_TYPE.get(inc.type, ("Inspect the site", "Mobile 500 GPM Dewatering Pump"))
        score = _job_score(inc.job_id)
        items.append({
            "key": inc.id[:8],
            "incident_id": inc.id,
            "id": f"CCTV-{inc.id[:6].upper()}",
            "source": "cctv",
            "camera": cam["id"] if cam else None,
            "location": loc["name"],
            "zone": loc["zone"],
            "title": inc.subtype.replace("_", " ").capitalize(),
            "category": _CATEGORY_BY_TYPE.get(inc.type, inc.type.capitalize()),
            "severity": inc.severity,
            "risk_score": f"{score:.0f}/100" if score is not None else "n/a",
            "description": inc.description,
            "reported_at": _ago(inc.job.created_at),
            "detail": f"{inc.job.filename} at {inc.video_ts} · confidence {inc.confidence:.0%}",
            "suggested_action": action,
            "machinery": machinery,
            "photo": incident_frame(inc),
        })
    return items


def _sensor_incidents(skip_locations: set) -> List[Dict[str, Any]]:
    """Demo incidents raised by drain sensors (no camera photo). Locations a camera
    has already reported on are left out so a site never appears twice."""
    items = []
    for item in PRIORITY_QUEUE:
        if item["location"] in skip_locations:
            continue
        items.append({
            "key": item["id"],
            "incident_id": None,
            "id": item["id"],
            "source": "sensor",
            "camera": None,
            "location": item["location"],
            "zone": item["zone"],
            "title": item["category"],
            "category": item["category"],
            "severity": item["severity"],
            "risk_score": f"{item['risk_score']}/100",
            "description": item["description"],
            "reported_at": item["reported_at"],
            "detail": f"Detected plate {item['plate_text']}" if item.get("plate_text") else "Drain level sensor and field report",
            "suggested_action": item["suggested_action"],
            "machinery": (
                "High Pressure Silt Jetting & Suction Tanker" if "Jetting" in item["suggested_action"]
                else "Mobile 500 GPM Dewatering Pump"
            ),
            "photo": None,
        })
    return items


def open_incidents() -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        cctv = _cctv_incidents(db)
    finally:
        db.close()
    items = cctv + _sensor_incidents({i["location"] for i in cctv})
    return sorted(items, key=lambda i: (-i["severity"], i["source"] != "cctv"))


def open_incident_count() -> int:
    """Open incidents plus violations waiting for review (sidebar badge)."""
    db = SessionLocal()
    try:
        pending = db.query(Violation).filter(Violation.review_status == "pending_review").count()
    finally:
        db.close()
    return len(open_incidents()) + pending


def _resolve_incident(incident_id: str, officer: str = "Duty officer") -> None:
    db = SessionLocal()
    try:
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if inc is not None:
            inc.status = "resolved"
            db.add(AuditLog(user=officer, action="resolved_incident", entity="incident", entity_id=inc.id))
            db.commit()
    finally:
        db.close()


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


def _pending_violations(db):
    return (
        db.query(Violation)
        .options(joinedload(Violation.incident).joinedload(Incident.evidences), joinedload(Violation.incident).joinedload(Incident.job))
        .join(Violation.incident).join(Incident.job)
        .filter(Violation.review_status == "pending_review")
        .order_by(Job.created_at.desc())
        .all()
    )


def render_violation_review():
    """Officer review of AI-detected dumping violations from uploaded videos."""
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
        pending = _pending_violations(db)
        if not pending:
            st.markdown(
                f'<div class="fg-noframe" style="aspect-ratio:auto;height:140px;">{icon("check", 22)}'
                f'No violations waiting. They appear here when a video is analysed with dumping detection on.</div>',
                unsafe_allow_html=True,
            )
            return

        st.caption(
            "Evidence goes to the municipal corporation only after you approve it. "
            "Check that the person is clearly dumping waste and that the plate matches the vehicle."
        )
        officer = st.text_input("Reviewing officer name", value=st.session_state.get("reviewing_officer", ""), key="reviewing_officer")

        for v in pending:
            inc = v.incident
            loc = location_for_job(inc.job.filename, inc.job.source_gps) if inc.job else PUNE_LOCATIONS[0]
            with st.container(key=f"fgincident_v_{v.id[:8]}"):
                plate = v.plate_text or "not legible"
                plate_note = "" if not v.plate_text else (" (valid format)" if v.plate_valid else " (unusual format, verify)")
                st.markdown(_flat(f"""
                <div class="fg-inc-head">
                  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                    {status_pill("High", f"Severity {inc.severity}/5")}
                    <span class="fg-inc-title">Dumping at {escape(loc['name'])}</span>
                    <span class="fg-src fg-src-cctv">{icon('camera', 12)} CCTV</span>
                  </div>
                  <span class="fg-mono" style="font-size:11px;color:#94A0B4;">{escape(inc.job.filename if inc.job else '?')} at {inc.video_ts}</span>
                </div>
                <div class="fg-inc-desc">{escape(inc.description)}</div>
                <div class="fg-kv" style="border-top:none;padding-top:0;margin-bottom:10px;">
                  <div><span class="fg-k">Vehicle</span><span class="fg-v">{escape(v.vehicle_type or 'On foot / none')}</span></div>
                  <div><span class="fg-k">Plate</span><span class="fg-v mono">{escape(plate)}{plate_note}</span></div>
                  <div><span class="fg-k">Plate legibility</span><span class="fg-v">{escape(str(v.plate_legibility))}</span></div>
                  <div><span class="fg-k">Model confidence</span><span class="fg-v mono">{inc.confidence:.0%}</span></div>
                </div>
                """), unsafe_allow_html=True)
                images = [(ev.kind, ev.path) for ev in inc.evidences if ev.kind in VIOLATION_EVIDENCE_LABELS and Path(ev.path).is_file()]
                images.sort(key=lambda kp: list(VIOLATION_EVIDENCE_LABELS).index(kp[0]))
                if images:
                    cols = st.columns(max(3, len(images)))
                    for i, (col, (kind, path)) in enumerate(zip(cols, images)):
                        with col, st.container(key=f"fgframe_v_{v.id[:8]}_{i}"):
                            st.image(path, caption=VIOLATION_EVIDENCE_LABELS[kind], use_container_width=True)
                else:
                    st.warning("No evidence images were saved for this violation.")

                a, r, _ = st.columns([1.4, 1, 3])
                if a.button("Approve and send to PMC", key=f"approve_{v.id}", type="primary", disabled=not officer.strip()):
                    st.session_state["violation_review_result"] = ("approved", _review_violation(v.id, "approved", officer.strip()))
                    st.rerun()
                if r.button("Reject", key=f"reject_{v.id}", disabled=not officer.strip()):
                    _review_violation(v.id, "rejected", officer.strip())
                    st.session_state["violation_review_result"] = ("rejected", [])
                    st.rerun()
    finally:
        db.close()


def _kpi(label: str, value: int, ico: str, color: str, note: str) -> str:
    return (
        f'<div class="fg-kpi" style="--kpi-c:{color}">'
        f'<div class="fg-kpi-label">{icon(ico, 15)}<span>{label}</span></div>'
        f'<div class="fg-kpi-row"><span class="fg-kpi-value">{value:02d}</span>'
        f'<span class="fg-kpi-delta">{note}</span></div></div>'
    )


def _render_incident(item: Dict[str, Any]) -> None:
    level = "Critical" if item["severity"] >= 5 else ("High" if item["severity"] >= 4 else "Medium")
    cam_note = f" · {item['camera']}" if item["camera"] else ""
    source = (
        f'<span class="fg-src fg-src-cctv">{icon("camera", 12)} CCTV{cam_note}</span>'
        if item["source"] == "cctv"
        else f'<span class="fg-src fg-src-sensor">{icon("gauge", 12)} Sensor report</span>'
    )
    with st.container(key=f"fgincident_{item['key']}"):
        photo_col, body_col = st.columns([1, 1.9], gap="medium")
        with photo_col:
            if item["photo"]:
                with st.container(key=f"fgframe_inc_{item['key']}"):
                    st.image(item["photo"], use_container_width=True)
                st.caption("Key frame saved from the video")
            else:
                st.markdown(
                    f'<div class="fg-noframe">{icon("gauge", 20)}<span>Sensor report<br>no camera frame</span></div>',
                    unsafe_allow_html=True,
                )
        with body_col:
            st.markdown(_flat(f"""
            <div class="fg-inc-head" style="box-shadow:inset 3px 0 0 {STATUS[level]['fg']};padding-left:10px;">
              <div style="min-width:0;">
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                  {status_pill(level, f"Severity {item['severity']}/5")}{source}
                </div>
                <div class="fg-inc-title" style="margin-top:6px;">{escape(item['location'])}
                  <span style="font-family:var(--fg-font-body);font-size:12.5px;font-weight:500;color:#64708A;"> &middot; {escape(item['title'])}</span>
                </div>
              </div>
              <span class="fg-mono" style="font-size:11px;color:#94A0B4;">{item['id']} &middot; {item['reported_at']}</span>
            </div>
            <div class="fg-inc-desc">{escape(item['description'])}</div>
            <div class="fg-kv">
              <div><span class="fg-k">Category</span><span class="fg-v">{escape(item['category'])}</span></div>
              <div><span class="fg-k">Risk score</span><span class="fg-v mono">{item['risk_score']}</span></div>
              <div><span class="fg-k">Suggested action</span><span class="fg-v">{escape(item['suggested_action'])}</span></div>
              <div><span class="fg-k">Evidence</span><span class="fg-v" style="font-size:12px;">{escape(item['detail'])}</span></div>
            </div>
            """), unsafe_allow_html=True)

            if item["incident_id"]:
                _, btn = st.columns([3, 1])
                if btn.button("Mark resolved", key=f"resolve_{item['key']}", use_container_width=True):
                    _resolve_incident(item["incident_id"])
                    st.toast(f"{item['title']} at {item['location']} marked resolved")
                    st.rerun()

        with st.expander("Crew for this site", expanded=False):
            render_crew_dispatch_widget(
                location_name=item["location"],
                key_prefix=f"pq_{item['key']}",
                suggested_machinery=item["machinery"],
                zone=item["zone"],
                incident_id=item["id"],
                header_title=None,
            )


def render_priority_queue_and_interventions():
    """Open incidents with evidence photos, violation review and crews in the field."""
    operations = init_operations_state()
    incidents = open_incidents()
    db = SessionLocal()
    try:
        pending_count = len(_pending_violations(db))
    finally:
        db.close()
    available_leads = get_available_leads()
    with_photos = sum(1 for i in incidents if i["photo"])

    st.markdown(page_header(
        "Priority queue",
        "Every incident found in CCTV video arrives here with its key frame. Review violations, then send a crew.",
        eyebrow="Operations",
        meta=[f"<b>{len(incidents)}</b> open incidents", f"<b>{len(operations)}</b> crews deployed",
              f"<b>{len(available_leads)}</b> engineers available"],
    ), unsafe_allow_html=True)

    toast_data = st.session_state.pop("deploy_success_data", None)
    if toast_data:
        st.toast(f"{toast_data['id']}: {toast_data['eq_type']} dispatched to {toast_data['target_loc']} (lead: {toast_data['crew_head']})")

    k1, k2, k3, k4 = st.columns(4)
    crit = sum(1 for i in incidents if i["severity"] >= 5)
    k1.markdown(_kpi("Open incidents", len(incidents), "alert", STATUS["Critical"]["fg"], f"<b>{crit}</b> severity 5"), unsafe_allow_html=True)
    k2.markdown(_kpi("With CCTV photos", with_photos, "camera", "#0A7C8F", "key frames attached"), unsafe_allow_html=True)
    k3.markdown(_kpi("Violations to review", pending_count, "shield", STATUS["High"]["fg"], "officer approval"), unsafe_allow_html=True)
    k4.markdown(_kpi("Crews in the field", len(operations), "truck", STATUS["Low"]["fg"], f"<b>{len(available_leads)}</b> engineers free"), unsafe_allow_html=True)
    st.write("")

    tab_inc, tab_viol, tab_crews = st.tabs([
        f"Open incidents ({len(incidents)})",
        f"Violations to review ({pending_count})",
        f"Crews in the field ({len(operations)})",
    ])

    with tab_inc:
        f1, f2 = st.columns([1.2, 3], vertical_alignment="bottom")
        source = f1.selectbox("Source", ["All sources", "CCTV only", "Sensor reports only"], label_visibility="collapsed")
        shown = [
            i for i in incidents
            if source == "All sources" or (source == "CCTV only") == (i["source"] == "cctv")
        ]
        f2.markdown(
            f'<div style="font-size:12px;color:#64708A;padding-bottom:10px;">Highest severity first. '
            f'Showing {len(shown)} of {len(incidents)}. Analysing a new video adds its findings here automatically.</div>',
            unsafe_allow_html=True,
        )
        if not shown:
            st.info("No open incidents for this filter.")
        for item in shown:
            _render_incident(item)

    with tab_viol:
        st.markdown(section_title(
            "Dumping violations awaiting review",
            "Detected in analysed CCTV video. Nothing is sent to the municipality until an officer approves it.",
        ), unsafe_allow_html=True)
        render_violation_review()

    with tab_crews:
        _render_crews(operations, incidents)


def _render_crews(operations: List[Dict[str, Any]], incidents: List[Dict[str, Any]]) -> None:
    st.markdown(section_title("Crews in the field", "Every active deployment. Recall a crew to free its engineer."), unsafe_allow_html=True)
    if not operations:
        st.info("No crews are deployed.")
    for idx, op in enumerate(list(operations)):
        card_col, btn_col = st.columns([5.2, 1], gap="small", vertical_alignment="center")
        with card_col:
            st.markdown(_flat(f"""
            <div class="fg-card" style="margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="font-size:14px; font-weight:600; color:#0B1220;">{op['type']}</span>
                        <span class="fg-mono" style="font-size:11px; color:#64708A;">{op['id']}</span>
                    </div>
                    <span style="font-size:12px; color:#047857; font-weight:500;">{op['status']}</span>
                </div>
                <div class="fg-kv">
                    <div><span class="fg-k">Location</span><span class="fg-v">{op['location']}</span></div>
                    <div><span class="fg-k">Unit lead</span><span class="fg-v">{op['crew_head']}</span></div>
                    <div><span class="fg-k">Water pumped</span><span class="fg-v mono">{op.get('water_discharged_m3', 0)} m&sup3;</span></div>
                    <div><span class="fg-k">Expected clear</span><span class="fg-v">{op.get('eta_cleared', '-')}</span></div>
                </div>
            </div>
            """), unsafe_allow_html=True)
        with btn_col:
            if st.button("Recall crew", key=f"demob_{op['id']}_{idx}", help=f"Recall crew from {op['location']}", use_container_width=True):
                operations.remove(op)
                st.session_state["operations_list"] = operations
                st.rerun()

    deployed = {op["location"].strip().lower() for op in operations}
    free_locations = [l["name"] for l in PUNE_LOCATIONS if l["name"].strip().lower() not in deployed]
    free_leads = [lead for lead in PUNE_MUNICIPAL_CREW_ROSTER if lead.strip().lower() not in {op["crew_head"].strip().lower() for op in operations}]

    with st.expander("Dispatch a crew to another location"):
        f1, f2 = st.columns(2)
        eq_type = f1.selectbox("Machinery", [
            "High Pressure Silt Jetting & Suction Tanker",
            "Mobile 500 GPM Dewatering Pump",
            "Mobile 1000 GPM Heavy Surcharge Pump",
            "Robotic Drain Cleaning Crawler",
            "Traffic Diversion Barricade Unit",
        ], key="gen_eq_type")
        target = f1.selectbox("Location (no crew yet)", free_locations, key="gen_target_loc") if free_locations else None
        lead = f2.selectbox("Engineer (available only)", free_leads, key="gen_crew_head") if free_leads else None
        priority = f2.selectbox("Priority", ["Priority 1 (within 10 min)", "Priority 2 (within 30 min)", "Routine Preventive"], key="gen_priority")
        if st.button("Dispatch crew", key="gen_deploy_btn", type="primary", disabled=not (target and lead)):
            new_id = f"OP-{700 + len(operations) + 1}"
            eta = "20 mins" if "10 min" in priority else ("45 mins" if "30 min" in priority else "1h 30m")
            st.session_state["operations_list"].insert(0, {
                "id": new_id, "type": eq_type, "location": target, "status": "Deployed & En Route",
                "crew_head": lead, "units": 1, "water_discharged_m3": 0, "eta_cleared": eta,
            })
            st.session_state["deploy_success_data"] = {
                "id": new_id, "eq_type": eq_type, "target_loc": target, "crew_head": lead,
                "priority": priority, "timestamp": time.time(),
            }
            st.rerun()


def render_priority_queue():
    """Alias for unified view."""
    render_priority_queue_and_interventions()
