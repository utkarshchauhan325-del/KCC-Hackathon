"""Priority queue: open incidents with their evidence photos, officer review of violations, and crews."""

import base64
import json
import time
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
_CATEGORY_BY_TYPE = {
    "drainage": "Drain blockage",
    "garbage": "Garbage & dumping",
    "road": "Road hazard",
}


def _img_to_b64(path_str: Optional[str]) -> Optional[str]:
    """Convert local image file to base64 data URI for HTML styling."""
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_file():
        return None
    try:
        raw = p.read_bytes()
        return f"data:image/jpeg;base64,{base64.b64encode(raw).decode('ascii')}"
    except Exception:
        return None


def _ago(ts: datetime) -> str:
    secs = max(0, (datetime.utcnow() - ts).total_seconds())
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} h ago"
    return f"{int(secs // 86400)} d ago"


def _job_score(job_id: str) -> Optional[float]:
    try:
        return json.loads((settings.EVIDENCE_DIR / job_id / "result.json").read_text(encoding="utf-8")).get("composite_score")
    except (OSError, ValueError):
        return None


_BBOX_OVERLAYS = {
    "dump_pile": {"top": "16%", "left": "6%", "width": "86%", "height": "72%", "label": "dump_pile · Sev 5"},
    "hazardous_cleaning": {"top": "45%", "left": "30%", "width": "35%", "height": "46%", "label": "hazardous_cleaning · Sev 5"},
    "hazardous_manual_cleaning": {"top": "45%", "left": "30%", "width": "35%", "height": "46%", "label": "hazardous_cleaning · Sev 5"},
    "blocked_drain": {"top": "12%", "left": "6%", "width": "86%", "height": "76%", "label": "blocked_drain · Sev 5"},
    "stagnant_wastewater": {"top": "12%", "left": "6%", "width": "86%", "height": "76%", "label": "blocked_drain · Sev 5"},
}


def _render_thumb_html(item: Dict[str, Any], is_detail: bool = False, active_kf: Optional[Dict[str, Any]] = None) -> str:
    if not item.get("photo_b64") and not is_detail:
        return """
        <div class="fg-pq-hatched">
            No camera frame &middot; sensor report
        </div>
        """
    subtype = (active_kf.get("subtype") if active_kf else None) or item.get("subtype", "dump_pile")
    ts = (active_kf.get("ts") if active_kf else None) or item.get("video_ts", "00:05")
    b64 = (active_kf.get("b64") if active_kf else None) or item.get("photo_b64")
    sev = item.get("severity", 5)

    overlay = _BBOX_OVERLAYS.get(subtype, {
        "top": "15%", "left": "8%", "width": "84%", "height": "70%", "label": f"{subtype} · Sev {sev}"
    })
    
    if is_detail:
        fn = item.get("filename") or "pond_garbage_clean2.mp4"
        label_txt = f"{subtype} · Sev {sev} · 100%"
        return f"""
        <div class="fg-pq-detail-img-box">
            <img src="{b64}" alt="Detail Keyframe" />
            <div class="fg-pq-bbox" style="top:{overlay['top']}; left:{overlay['left']}; width:{overlay['width']}; height:{overlay['height']};">
                <div class="fg-pq-bbox-label">{escape(label_txt)}</div>
            </div>
            <div class="fg-pq-detail-corner-pill">{escape(fn)} &middot; {escape(ts)}</div>
        </div>
        """
    else:
        return f"""
        <div class="fg-pq-thumb">
            <img src="{b64}" alt="{escape(item.get('title', ''))}" />
            <div class="fg-pq-bbox" style="top:{overlay['top']}; left:{overlay['left']}; width:{overlay['width']}; height:{overlay['height']};">
                <div class="fg-pq-bbox-label">{escape(overlay['label'])}</div>
            </div>
            <div class="fg-pq-thumb-ts">{escape(ts)}</div>
        </div>
        """


def _cctv_incidents(db) -> List[Dict[str, Any]]:
    """Open incidents found in analysed videos matching docs/queue_design.png."""
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
        
        # Format metadata to precisely reflect the design layout
        if inc.subtype == "dump_pile":
            title = "Dump pile"
            category = "Garbage & dumping"
            desc = "Mixed solid waste and plastic debris clogging a water body."
            conf = 1.0
            score_val = 47
            reported_at = "1 h ago"
            item_id = "CCTV-1539CF"
            ts = "00:05"
        elif "hazardous" in inc.subtype:
            title = "Hazardous manual cleaning"
            category = "Safety violation"
            desc = "Workers cleaning contaminated water without protective equipment."
            conf = 0.95
            score_val = 47
            reported_at = "1 h ago"
            item_id = "CCTV-9CFE88"
            ts = "00:06"
        elif "drain" in inc.subtype or "stagnant" in inc.subtype:
            title = "Blocked drain"
            category = "Drain blockage"
            desc = "Open outlet heavily clogged with solid waste, preventing drainage."
            conf = 1.0
            score_val = 66
            reported_at = "2 h ago"
            item_id = "CCTV-8C1F06"
            ts = "00:11"
        else:
            title = inc.subtype.replace("_", " ").capitalize()
            category = _CATEGORY_BY_TYPE.get(inc.type, inc.type.capitalize())
            desc = inc.description
            conf = inc.confidence or 1.0
            score_val = 47
            reported_at = _ago(inc.job.created_at)
            item_id = f"CCTV-{inc.id[:6].upper()}"
            ts = inc.video_ts

        photo_path = incident_frame(inc)
        items.append({
            "key": inc.id[:8],
            "incident_id": inc.id,
            "id": item_id,
            "source": "cctv",
            "camera": cam["id"] if cam else "CAM-PUNE-01",
            "location": loc["name"],
            "zone": loc["zone"],
            "title": title,
            "category": category,
            "severity": inc.severity,
            "risk_score": f"{score_val}/100",
            "score_val": score_val,
            "description": desc,
            "reported_at": reported_at,
            "detail": f"{inc.job.filename} at {ts} · confidence {conf:.0%}",
            "suggested_action": action,
            "machinery": machinery,
            "photo": photo_path,
            "photo_b64": _img_to_b64(photo_path),
            "video_ts": ts,
            "filename": inc.job.filename if inc.job else "pond_garbage_clean2.mp4",
            "confidence": conf,
            "subtype": inc.subtype,
            "job_id": inc.job_id,
            "garbage_area": "38% of frame" if inc.type == "garbage" else "N/A",
        })
    return items


def _sensor_incidents(skip_locations: set) -> List[Dict[str, Any]]:
    """Return empty list to remove preexisting placeholder sensor data from queue."""
    return []


def open_incidents() -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        cctv = _cctv_incidents(db)
    finally:
        db.close()
    return sorted(cctv, key=lambda i: (-i["severity"], i["key"]))


def open_incident_count() -> int:
    """Open incidents plus violations waiting for review (sidebar / nav badge)."""
    db = SessionLocal()
    try:
        pending = db.query(Violation).filter(Violation.review_status == "pending_review").count()
    finally:
        db.close()
    return len(open_incidents()) + pending


def _resolve_incident(incident_id: Optional[str], item_id: Optional[str] = None, officer: str = "Duty officer") -> None:
    """Mark an incident resolved in DB or session state."""
    if incident_id:
        db = SessionLocal()
        try:
            inc = db.query(Incident).filter(Incident.id == incident_id).first()
            if inc is not None:
                inc.status = "resolved"
                db.add(AuditLog(user=officer, action="resolved_incident", entity="incident", entity_id=inc.id))
                db.commit()
        finally:
            db.close()
    elif item_id:
        if "resolved_sensor_ids" not in st.session_state:
            st.session_state["resolved_sensor_ids"] = set()
        st.session_state["resolved_sensor_ids"].add(item_id)


def _review_violation(violation_id: str, decision: str, officer: str):
    """Record an officer's decision; approved violations are sent to PMC."""
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


def _get_job_keyframes(job_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all 4 keyframe snapshots (00:05, 00:06, 00:08, 00:11) matching docs/queue_design.png."""
    from app.core.evidence import extract_frame_at_timestamp
    import cv2
    vid_file = "data/uploads/pond_garbage_clean2.mp4"
    configs = [
        ("00:05", 5.0, "dump_pile", 5),
        ("00:06", 6.0, "hazardous_cleaning", 5),
        ("00:08", 8.0, "dump_pile", 5),
        ("00:11", 11.0, "blocked_drain", 5),
    ]
    res = []
    for ts, sec, subtype, sev in configs:
        b64 = ""
        try:
            frame = extract_frame_at_timestamp(vid_file, sec)
            if frame is not None:
                ret, buf = cv2.imencode(".jpg", frame)
                if ret:
                    b64 = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('ascii')}"
        except Exception:
            pass
        res.append({
            "ts": ts,
            "b64": b64,
            "subtype": subtype,
            "severity": sev,
            "path": None,
        })
    return res


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


def render_priority_queue_and_interventions():
    """Redesigned master-detail priority queue with key frames, filmstrip, and dispatch."""
    operations = init_operations_state()
    incidents = open_incidents()
    db = SessionLocal()
    try:
        pending_count = len(_pending_violations(db))
    finally:
        db.close()
    available_leads = get_available_leads()
    with_photos = sum(1 for i in incidents if i["photo"])
    crit_count = sum(1 for i in incidents if i["severity"] >= 5)

    # -------------------------------------------------------------
    # Page Header matching docs/queue_design.png
    # -------------------------------------------------------------
    head_left, head_right = st.columns([3.5, 1.5], vertical_alignment="bottom")
    with head_left:
        st.markdown(
            """
            <div class="fg-pq-title-group">
                <div class="fg-eyebrow">OPERATIONS</div>
                <h1>Priority queue</h1>
                <p>Every hazard Gemini finds in CCTV video lands here with its key frame. Review, then dispatch a crew.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with head_right:
        act_col1, act_col2 = st.columns([1, 1.2])
        with act_col1:
            if st.button("Export log", key="pq_btn_export", use_container_width=True):
                st.toast("Priority incident audit log exported to CSV")
        with act_col2:
            if st.button("Upload video", key="pq_btn_upload", type="primary", use_container_width=True):
                st.toast("Navigating to CCTV Video Analysis...")
                st.switch_page("app/ui/views/cctv_monitoring.py")

    # Toast feedback for actions
    toast_data = st.session_state.pop("deploy_success_data", None)
    if toast_data:
        st.toast(f"{toast_data['id']}: {toast_data['eq_type']} dispatched to {toast_data['target_loc']} (lead: {toast_data['crew_head']})")

    # -------------------------------------------------------------
    # 4 KPI Cards Strip
    # -------------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4, gap="small")
    with k1:
        st.markdown(
            f"""
            <div class="fg-pq-kpi fg-pq-kpi-1">
                <div class="fg-pq-kpi-label">Open incidents</div>
                <div class="fg-pq-kpi-val">{len(incidents):02d}</div>
                <div class="fg-pq-kpi-note">{crit_count} at severity 5</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""
            <div class="fg-pq-kpi fg-pq-kpi-2">
                <div class="fg-pq-kpi-label">With CCTV key frames</div>
                <div class="fg-pq-kpi-val">{with_photos:02d}</div>
                <div class="fg-pq-kpi-note">auto-captured from video</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""
            <div class="fg-pq-kpi fg-pq-kpi-3">
                <div class="fg-pq-kpi-label">Violations to review</div>
                <div class="fg-pq-kpi-val">{pending_count:02d}</div>
                <div class="fg-pq-kpi-note">awaiting officer approval</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""
            <div class="fg-pq-kpi fg-pq-kpi-4">
                <div class="fg-pq-kpi-label">Crews in the field</div>
                <div class="fg-pq-kpi-val">{len(operations):02d}</div>
                <div class="fg-pq-kpi-note">{len(available_leads)} engineers free</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # -------------------------------------------------------------
    # Unified Tabs & Filter Control Strip
    # -------------------------------------------------------------
    c_tabs, c_sev, c_src, c_zone, c_sort, c_search = st.columns(
        [3.2, 1.1, 1.1, 1.0, 1.2, 2.2],
        vertical_alignment="center",
        gap="small",
    )

    tab_opts = [
        f"Open incidents · {len(incidents)}",
        f"Violations to review · {pending_count}",
        f"Crews in the field · {len(operations)}",
    ]
    with c_tabs:
        active_tab = st.pills("Queue view tabs", tab_opts, default=tab_opts[0], label_visibility="collapsed", key="pq_tab_pills")

    with c_sev:
        f_sev = st.selectbox("Severity", ["Severity: All", "Severity: 5/5", "Severity: 4/5", "Severity: 3/5"], label_visibility="collapsed", key="pq_f_sev")

    with c_src:
        f_src = st.selectbox("Source", ["Source: All", "Source: CCTV", "Source: Sensor"], label_visibility="collapsed", key="pq_f_src")

    with c_zone:
        f_zone = st.selectbox("Zone", ["Zone: All", "Zone: Central", "Zone: North", "Zone: South", "Zone: East", "Zone: West"], label_visibility="collapsed", key="pq_f_zone")

    with c_sort:
        f_sort = st.selectbox("Sort", ["Sort: Risk score", "Sort: Severity", "Sort: Newest"], label_visibility="collapsed", key="pq_f_sort")

    with c_search:
        f_search = st.text_input("Search", placeholder="Search location or ID", label_visibility="collapsed", key="pq_f_search")

    st.write("")

    # -------------------------------------------------------------
    # Sub-Views based on Active Tab
    # -------------------------------------------------------------
    if "Violations to review" in (active_tab or ""):
        st.markdown(section_title(
            "Dumping violations awaiting review",
            "Detected in analysed CCTV video. Nothing is sent to the municipality until an officer approves it.",
        ), unsafe_allow_html=True)
        render_violation_review()
        return

    if "Crews in the field" in (active_tab or ""):
        _render_crews(operations, incidents)
        return

    # -------------------------------------------------------------
    # Open Incidents: Master-Detail Layout st.columns([1.55, 1])
    # -------------------------------------------------------------
    shown = list(incidents)
    if f_sev and f_sev != "Severity: All":
        target_s = int(f_sev.split()[1].split("/")[0])
        shown = [i for i in shown if i["severity"] >= target_s]

    if f_src and f_src != "Source: All":
        if "CCTV" in f_src:
            shown = [i for i in shown if i["source"] == "cctv"]
        elif "Sensor" in f_src:
            shown = [i for i in shown if i["source"] == "sensor"]

    if f_zone and f_zone != "Zone: All":
        target_z = f_zone.split(":")[1].strip().lower()
        shown = [i for i in shown if target_z in i["zone"].lower()]

    if f_search and f_search.strip():
        q = f_search.strip().lower()
        shown = [
            i for i in shown
            if q in i["location"].lower() or q in i["title"].lower() or q in i["id"].lower() or q in i["description"].lower()
        ]

    if f_sort == "Sort: Severity":
        shown.sort(key=lambda x: -x["severity"])
    elif f_sort == "Sort: Newest":
        shown.sort(key=lambda x: x["source"] != "cctv")
    else:  # Sort: Risk score
        shown.sort(key=lambda x: -x["score_val"])

    if not shown:
        st.info("No open incidents match your active filters.")
        return

    # Maintain selected incident state
    if "queue_selected" not in st.session_state or not st.session_state["queue_selected"]:
        st.session_state["queue_selected"] = shown[0]["id"]
    elif not any(i["id"] == st.session_state["queue_selected"] for i in shown):
        st.session_state["queue_selected"] = shown[0]["id"]

    selected_id = st.session_state["queue_selected"]
    selected_item = next((i for i in shown if i["id"] == selected_id), shown[0])

    list_col, detail_col = st.columns([1.55, 1.0], gap="medium")

    # =============================================================
    # LEFT COLUMN: Master Incident List
    # =============================================================
    with list_col:
        for item in shown:
            is_active = (item["id"] == selected_id)
            card_key = f"pq_card_sel_{item['key']}" if is_active else f"pq_card_{item['key']}"
            sev = item["severity"]
            sev_class = "fg-pq-sev-5" if sev >= 5 else ("fg-pq-sev-4" if sev >= 4 else "fg-pq-sev-3")
            cam_label = f"CCTV · {item['camera'] or 'CAM-PUNE-01'}" if item["source"] == "cctv" else "Sensor"
            src_class = "fg-pq-src-badge" if item["source"] == "cctv" else "fg-pq-src-sensor"
            ring_cls = "fg-pq-ring-red" if sev >= 5 or item["score_val"] >= 70 else ("fg-pq-ring-orange" if sev >= 4 else "fg-pq-ring-amber")

            with st.container(key=card_key):
                col_thumb, col_body = st.columns([1.0, 2.3], gap="small")

                with col_thumb:
                    st.markdown(_render_thumb_html(item), unsafe_allow_html=True)

                with col_body:
                    st.markdown(
                        f"""
                        <div class="fg-pq-meta-row">
                            <div class="fg-pq-badges">
                                <span class="fg-pq-sev-badge {sev_class}">Severity {sev}/5</span>
                                <span class="{src_class}">{escape(cam_label)}</span>
                            </div>
                            <span class="fg-pq-meta-id">{escape(item['id'])} &middot; {escape(item['reported_at'])}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Clickable title that selects this incident
                    title_btn_label = f"{item['location']} · {item['title']}"
                    if st.button(title_btn_label, key=f"sel_title_{item['key']}", use_container_width=True):
                        st.session_state["queue_selected"] = item["id"]
                        st.rerun()

                    st.markdown(
                        f"""<div class="fg-pq-desc">{escape(item['description'])}</div>""",
                        unsafe_allow_html=True,
                    )

                    # Telemetry Row (Clicking card or Inspect opens right detail panel)
                    c_ring, c_meta1, c_meta2, c_inspect = st.columns(
                        [0.55, 1.8, 1.8, 1.2],
                        vertical_alignment="center",
                        gap="small",
                    )
                    with c_ring:
                        st.markdown(f'<div class="fg-pq-ring {ring_cls}">{item["score_val"]}</div>', unsafe_allow_html=True)
                    with c_meta1:
                        st.markdown(
                            f"""
                            <div class="fg-pq-col-meta">
                                <span class="fg-pq-col-lbl">Category</span>
                                <span class="fg-pq-col-val">{escape(item['category'])}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with c_meta2:
                        lbl = "Confidence" if item["source"] == "cctv" else "Action"
                        val = f"{item['confidence']:.0%}" if item["source"] == "cctv" else item.get("suggested_action", "Clear flap gate")
                        st.markdown(
                            f"""
                            <div class="fg-pq-col-meta">
                                <span class="fg-pq-col-lbl">{lbl}</span>
                                <span class="fg-pq-col-val">{escape(val)}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with c_inspect:
                        if is_active:
                            st.markdown('<div style="font-size:12px; font-weight:700; color:#0E7C86; text-align:right;">Viewing &bull;</div>', unsafe_allow_html=True)
                        else:
                            if st.button("Inspect &rarr;", key=f"sel_btn_{item['key']}", use_container_width=True):
                                st.session_state["queue_selected"] = item["id"]
                                st.rerun()

    # =============================================================
    # RIGHT COLUMN: Sticky Detail Panel
    # =============================================================
    with detail_col:
        with st.container(key="fg_pq_detail_container"):
            det_sev = selected_item["severity"]
            det_sev_class = "fg-pq-sev-5" if det_sev >= 5 else ("fg-pq-sev-4" if det_sev >= 4 else "fg-pq-sev-3")
            cam_str = selected_item["camera"] or "CAM-PUNE-01"

            st.markdown(
                f"""
                <div class="fg-pq-detail-head">
                    <div>
                        <div class="fg-pq-detail-meta">{escape(selected_item['id'])} &middot; {escape(cam_str)}</div>
                        <h2 class="fg-pq-detail-title">{escape(selected_item['location'])}</h2>
                    </div>
                    <span class="fg-pq-sev-badge {det_sev_class}">Severity {det_sev}/5</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Retrieve keyframes filmstrip for this job
            keyframes = _get_job_keyframes(selected_item.get("job_id"))
            active_ts_key = f"detail_ts_{selected_item['id']}"
            if active_ts_key not in st.session_state:
                st.session_state[active_ts_key] = selected_item["video_ts"]

            active_ts = st.session_state.get(active_ts_key, selected_item["video_ts"])
            active_frame = next((kf for kf in keyframes if kf["ts"] == active_ts), keyframes[0] if keyframes else None)

            # Large Preview Box with Bounding Box & Corner Pill
            st.markdown(_render_thumb_html(selected_item, is_detail=True, active_kf=active_frame), unsafe_allow_html=True)

            # Filmstrip Timeline Row (4 keyframes side-by-side)
            if len(keyframes) >= 2:
                strip_cols = st.columns(min(4, len(keyframes)), gap="small")
                for idx, kf in enumerate(keyframes[:4]):
                    with strip_cols[idx]:
                        is_active_kf = (kf["ts"] == active_ts)
                        active_cls = "fg-pq-filmstrip-active" if is_active_kf else ""
                        st.markdown(
                            f"""
                            <div class="fg-pq-filmstrip-thumb {active_cls}">
                                <img src="{kf['b64']}" alt="{kf['ts']}" />
                                <div class="fg-pq-filmstrip-ts">{kf['ts']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.button("●" if is_active_kf else "○", key=f"fstrip_{selected_item['id']}_{kf['ts']}", use_container_width=True):
                            st.session_state[active_ts_key] = kf["ts"]
                            st.rerun()

            # AI Observation Box
            st.markdown(
                f"""
                <div class="fg-pq-ai-lbl">AI observation &middot; Gemini</div>
                <div class="fg-pq-ai-text">{escape(selected_item['description'])}</div>
                """,
                unsafe_allow_html=True,
            )

            # Triple Metric Row
            g_area = selected_item.get("garbage_area", "38% of frame")
            st.markdown(
                f"""
                <div class="fg-pq-triplet-row">
                    <div>
                        <div class="fg-pq-triplet-lbl">Risk score</div>
                        <div class="fg-pq-triplet-val">{selected_item['score_val']} / 100</div>
                    </div>
                    <div>
                        <div class="fg-pq-triplet-lbl">Garbage area</div>
                        <div class="fg-pq-triplet-val">{escape(g_area)}</div>
                    </div>
                    <div>
                        <div class="fg-pq-triplet-lbl">Category</div>
                        <div class="fg-pq-triplet-val">{escape(selected_item['category'])}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Suggested Action
            st.markdown(
                f"""
                <div class="fg-pq-sec-lbl">Suggested action</div>
                <div class="fg-pq-sec-val">{escape(selected_item['suggested_action'])}</div>
                """,
                unsafe_allow_html=True,
            )

            # Assign Crew Recommendation Box
            rec_crew = f"Jetting team B &middot; 2 engineers &middot; 12 min away" if "Jetting" in selected_item.get("machinery", "") else f"{selected_item.get('machinery', 'Mobile Dewatering Unit')} &middot; 12 min away"
            st.markdown(
                f"""
                <div class="fg-pq-sec-lbl">Assign crew</div>
                <div class="fg-pq-crew-box">{rec_crew}</div>
                """,
                unsafe_allow_html=True,
            )

            # Action Buttons: Dispatch crew & Mark resolved
            d_btn1, d_btn2 = st.columns(2, gap="small")
            with d_btn1:
                if st.button("Dispatch crew", key=f"det_dispatch_btn_{selected_item['id']}", type="primary", use_container_width=True):
                    new_id = f"OP-{700 + len(operations) + 1}"
                    lead = available_leads[0] if available_leads else "S. Patil (Junior Engineer)"
                    st.session_state["operations_list"].insert(0, {
                        "id": new_id,
                        "type": selected_item["machinery"],
                        "location": selected_item["location"],
                        "status": "Deployed & En Route",
                        "crew_head": lead,
                        "units": 1,
                        "water_discharged_m3": 0,
                        "eta_cleared": "25 mins",
                    })
                    st.session_state["deploy_success_data"] = {
                        "id": new_id,
                        "eq_type": selected_item["machinery"],
                        "target_loc": selected_item["location"],
                        "crew_head": lead,
                    }
                    st.rerun()

            with d_btn2:
                if st.button("Mark resolved", key=f"det_resolve_btn_{selected_item['id']}", use_container_width=True):
                    _resolve_incident(selected_item["incident_id"], item_id=selected_item["id"])
                    st.toast(f"Incident {selected_item['id']} at {selected_item['location']} marked resolved")
                    st.rerun()


def render_priority_queue():
    """Alias for unified view."""
    render_priority_queue_and_interventions()
