"""Priority queue: open incidents with their evidence photos, officer review of violations, and crews."""

import base64
import json
import time
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from sqlalchemy.orm import joinedload

from app.config import settings
from app.db.models import AuditLog, Incident, Job, Task, TaskSubmission, Violation, Worker, generate_uuid
from app.db.session import SessionLocal
from app.notify.alerts import send_incident_alert, send_task_assignment_alert, send_work_verified_alert
from app.ui.components.crew_dispatch import (
    PUNE_MUNICIPAL_CREW_ROSTER,
    get_available_leads,
    init_operations_state,
    render_crew_dispatch_widget,
)
from app.ui.components.evidence_frames import incident_frame
from app.core.plates import is_car_or_bike, analyze_plate_text, render_hsrp_badge_html
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
    subtype = (active_kf.get("subtype") if active_kf else None) or item.get("subtype", "dump_pile")
    ts = (active_kf.get("ts") if active_kf else None) or item.get("video_ts", "00:05")
    
    b64 = None
    if active_kf and active_kf.get("b64"):
        b64 = active_kf["b64"]
    if not b64:
        b64 = item.get("photo_b64")

    if not b64 and not is_detail:
        return """
        <div class="fg-pq-hatched">
            No camera frame &middot; sensor report
        </div>
        """
    
    sev = item.get("severity", 5)
    overlay = _BBOX_OVERLAYS.get(subtype, {
        "top": "15%", "left": "8%", "width": "84%", "height": "70%", "label": f"{subtype} · Sev {sev}"
    })
    
    if is_detail:
        fn = item.get("filename") or "video.mp4"
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
    """Open incidents found in analysed videos with assigned worker information."""
    rows = (
        db.query(Incident)
        .options(
            joinedload(Incident.evidences),
            joinedload(Incident.job),
            joinedload(Incident.tasks).joinedload(Task.worker),
        )
        .join(Incident.job)
        .filter(
            Incident.status.in_(["new", "assigned", "in_progress", "manual_review", "awaiting_verification"]),
            Incident.subtype != "dumping_violation",
            Job.status == "completed",
        )
        .order_by(Job.created_at.desc(), Incident.severity.desc())
        .all()
    )
    cam_by_loc = {c["location_id"]: c for c in ASSIGNED_CAMERAS}
    items, seen = [], set()
    for inc in rows:
        if inc.id in seen:
            continue
        seen.add(inc.id)
        
        loc = location_for_job(inc.job.filename, inc.job.source_gps)
        if inc.job and ("vehical" in inc.job.filename or "vehicle" in inc.job.filename):
            loc = next((l for l in PUNE_LOCATIONS if l["id"] == "LOC-02"), loc)

        cam = cam_by_loc.get(loc["id"])
        action, machinery = _ACTION_BY_TYPE.get(inc.type, ("Inspect the site", "Mobile 500 GPM Dewatering Pump"))
        
        title = inc.subtype.replace("_", " ").capitalize()
        category = _CATEGORY_BY_TYPE.get(inc.type, inc.type.capitalize())
        desc = inc.description or f"AI detected {title.lower()} requiring immediate inspection."
        conf = inc.confidence or 0.95
        score_val = int(min(100, max(25, inc.severity * 15 + int(conf * 20))))
        reported_at = _ago(inc.job.created_at) if inc.job and inc.job.created_at else "1 h ago"
        item_id = f"CCTV-{inc.id[:6].upper()}"
        ts = inc.video_ts or "00:05"

        photo_path = incident_frame(inc)
        annotated_path = next((e.path for e in inc.evidences if e.kind == "annotated" and Path(e.path).is_file()), None)
        raw_path = next((e.path for e in inc.evidences if e.kind == "frame" and Path(e.path).is_file()), None)
        video_path = next((e.path for e in inc.evidences if e.kind == "annotated_video" and Path(e.path).is_file()), None)

        if not video_path and inc.job_id:
            cand = Path("data/evidence") / inc.job_id / f"surveillance_{inc.job_id}_annotated.mp4"
            if cand.is_file():
                video_path = str(cand)
        if not video_path and inc.job and inc.job.filename:
            cand_upload = Path("data/uploads") / inc.job.filename
            if cand_upload.is_file():
                video_path = str(cand_upload)

        # Violation / object crops in the same job
        crops = []
        if inc.job:
            for job_inc in inc.job.incidents:
                for ev in job_inc.evidences:
                    if ev.kind in VIOLATION_EVIDENCE_LABELS and ev.kind != "frame" and Path(ev.path).is_file():
                        crops.append({
                            "kind": ev.kind,
                            "path": ev.path,
                            "label": VIOLATION_EVIDENCE_LABELS.get(ev.kind, ev.kind.replace("_", " ").capitalize())
                        })

        assigned_worker = None
        task_status = "unassigned"
        task_id = None
        task_due = None
        task_instructions = None
        if inc.tasks:
            latest_t = inc.tasks[-1]
            task_id = latest_t.id
            task_status = latest_t.status
            task_due = latest_t.due_at
            task_instructions = latest_t.instructions
            if latest_t.worker:
                assigned_worker = latest_t.worker.name

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
            "annotated_path": annotated_path,
            "raw_path": raw_path,
            "video_path": video_path,
            "crops": crops,
            "video_ts": ts,
            "filename": inc.job.filename if inc.job else "pond_garbage_clean2.mp4",
            "confidence": conf,
            "subtype": inc.subtype,
            "job_id": inc.job_id,
            "garbage_area": "38% of frame" if inc.type == "garbage" else "N/A",
            "assigned_worker": assigned_worker,
            "task_status": task_status,
            "task_id": task_id,
            "task_due": task_due,
            "task_instructions": task_instructions,
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
            "photo": item.get("evidence_crop"),
            "plate_text": item.get("plate_text"),
        })
    return items


def open_incidents() -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        cctv = _cctv_incidents(db)
    finally:
        db.close()
    return sorted(cctv, key=lambda i: (-i["severity"], i["key"]))


def open_incident_count() -> int:
    """Open incidents plus violations and manual reviews waiting for review."""
    db = SessionLocal()
    try:
        pending_v = db.query(Violation).filter(Violation.review_status == "pending_review").count()
        manual_t = db.query(Task).filter(Task.status == "manual_review").count()
        open_i = db.query(Incident).filter(
            Incident.status.in_(["new", "assigned", "in_progress", "manual_review", "awaiting_verification"]),
            Incident.subtype != "dumping_violation",
        ).count()
        return open_i + pending_v + manual_t
    finally:
        db.close()


def _manual_review_items(db) -> List[Dict[str, Any]]:
    tasks = (
        db.query(Task)
        .options(
            joinedload(Task.incident).joinedload(Incident.evidences),
            joinedload(Task.incident).joinedload(Incident.job),
            joinedload(Task.worker),
            joinedload(Task.submissions),
        )
        .filter(Task.status == "manual_review")
        .order_by(Task.assigned_at.desc())
        .all()
    )
    items = []
    for t in tasks:
        inc = t.incident
        loc = location_for_job(inc.job.filename, inc.job.source_gps) if inc.job else PUNE_LOCATIONS[0]
        before_photo = None
        for ev in inc.evidences:
            if ev.kind in ("annotated", "frame") and Path(ev.path).is_file():
                before_photo = ev.path
                break
        
        latest_sub = t.submissions[-1] if t.submissions else None
        reasons = []
        if latest_sub and latest_sub.rejection_reasons:
            try:
                reasons = json.loads(latest_sub.rejection_reasons) if latest_sub.rejection_reasons.startswith("[") else [latest_sub.rejection_reasons]
            except Exception:
                reasons = [str(latest_sub.rejection_reasons)]

        items.append({
            "task_id": t.id,
            "incident_id": inc.id,
            "subtype": inc.subtype.replace("_", " ").title(),
            "severity": inc.severity,
            "location": loc["name"],
            "zone": loc.get("zone", "Central"),
            "worker_name": t.worker.name if t.worker else "Unknown",
            "worker_phone": t.worker.phone if t.worker else "",
            "instructions": t.instructions,
            "before_photo": before_photo,
            "after_photo": latest_sub.after_photo_path if latest_sub else None,
            "attempt_number": latest_sub.attempt_number if latest_sub else len(t.submissions),
            "submitted_at": latest_sub.submitted_at if latest_sub else None,
            "gemini_confidence": latest_sub.gemini_confidence if latest_sub else 0.5,
            "garbage_after_pct": latest_sub.yoloe_garbage_after_pct if latest_sub else 0.0,
            "reasons": reasons,
            "worker_notes": latest_sub.worker_notes if latest_sub else None,
            "submission_id": latest_sub.id if latest_sub else None,
        })
    return items


def render_manual_review_tab():
    """Supervisor review of borderline or 3-attempt escalated worker proofs."""
    db = SessionLocal()
    try:
        items = _manual_review_items(db)
        if not items:
            st.markdown(
                """
                <div class="fg-noframe" style="aspect-ratio:auto; height:160px; padding:30px; text-align:center;">
                    <div style="font-size:24px; margin-bottom:8px;">✅</div>
                    <div style="font-size:15px; font-weight:600; color:#0F172A;">No Submissions Awaiting Manual Review</div>
                    <div style="font-size:13px; color:#64748B;">All worker submissions were automatically verified by AI or are in progress.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        st.caption("Review submissions where AI detected borderline confidence, residual debris, or reached the 3-attempt threshold. Approving marks the task verified and resolves the municipal incident.")

        for it in items:
            with st.container(key=f"fg_mr_card_{it['task_id'][:8]}"):
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:14px; margin-bottom:14px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <div>
                                <span class="fg-pq-sev-badge fg-pq-sev-{min(5, max(3, it['severity']))}">Severity {it['severity']}/5</span>
                                <span style="font-family:var(--fg-font-head); font-weight:700; font-size:16px; color:#0F172A; margin-left:8px;">
                                    {escape(it['location'])} &bull; <span style="color:#0E7C86;">{escape(it['subtype'])}</span>
                                </span>
                            </div>
                            <span style="background:#D9770618; color:#D97706; border:1px solid #D9770640; font-size:11px; font-weight:700; padding:3px 8px; border-radius:6px; text-transform:uppercase;">
                                Escalated (Attempt {it['attempt_number']}/3)
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                c_bef, c_aft, c_eval = st.columns([1, 1, 1.2], gap="medium")

                with c_bef:
                    if it["before_photo"] and Path(it["before_photo"]).is_file():
                        st.image(it["before_photo"], caption=f"Reported Hazard (Severity {it['severity']}/5)", use_container_width=True)
                    else:
                        st.markdown('<div class="fg-pq-hatched" style="height:160px;">Before proof unavailable</div>', unsafe_allow_html=True)

                with c_aft:
                    if it["after_photo"] and Path(it["after_photo"]).is_file():
                        st.image(it["after_photo"], caption=f"Worker Proof (Attempt {it['attempt_number']})", use_container_width=True)
                    else:
                        st.markdown('<div class="fg-pq-hatched" style="height:160px;">Submitted photo unavailable</div>', unsafe_allow_html=True)

                with c_eval:
                    reasons_html = "".join([f"<li>{escape(r)}</li>" for r in it["reasons"]]) if it["reasons"] else "<li>Escalated after multiple clearance attempts</li>"
                    st.markdown(
                        f"""
                        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:12px; font-size:12.5px;">
                            <div style="font-weight:700; color:#0F172A; margin-bottom:6px;">AI Verification Telemetry</div>
                            <div style="color:#475569; margin-bottom:4px;">&bull; Worker: <b>{escape(it['worker_name'])}</b> ({escape(it['worker_phone'])})</div>
                            <div style="color:#475569; margin-bottom:4px;">&bull; Residual Waste Area: <b>{it['garbage_after_pct']:.1f}%</b></div>
                            <div style="color:#475569; margin-bottom:4px;">&bull; VLM Confidence: <b>{it['gemini_confidence']:.0%}</b></div>
                            <div style="color:#475569; margin-bottom:6px;">&bull; Worker Notes: <i>{escape(it['worker_notes'] or 'None')}</i></div>
                            <div style="font-weight:700; color:#B45309; margin-top:8px; margin-bottom:4px;">Escalation Reasons:</div>
                            <ul style="margin:0; padding-left:16px; color:#9A3412;">{reasons_html}</ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    officer_name = st.text_input(
                        "Reviewing Officer Name",
                        value=st.session_state.get("reviewing_officer", "Duty Officer"),
                        key=f"mr_off_inp_{it['task_id']}",
                    )

                    b_appr, b_rej = st.columns(2, gap="small")
                    with b_appr:
                        if st.button("✅ Approve & Resolve", key=f"mr_appr_{it['task_id']}", type="primary", use_container_width=True):
                            db_act = SessionLocal()
                            try:
                                t_db = db_act.query(Task).filter(Task.id == it["task_id"]).first()
                                if t_db:
                                    t_db.status = "verified"
                                    if t_db.incident:
                                        t_db.incident.status = "resolved"
                                    if t_db.submissions:
                                        t_db.submissions[-1].verification_status = "verified"
                                        t_db.submissions[-1].reviewed_by = officer_name
                                        t_db.submissions[-1].reviewed_at = datetime.utcnow()
                                    db_act.add(AuditLog(
                                        user=officer_name,
                                        action="manual_review_approved",
                                        entity="task",
                                        entity_id=t_db.id,
                                    ))
                                    db_act.commit()
                                    send_work_verified_alert(db_act, t_db, t_db.submissions[-1] if t_db.submissions else None)
                                st.toast(f"Approved! Task {it['task_id'][:6]} verified and incident resolved.")
                                st.rerun()
                            finally:
                                db_act.close()

                    with b_rej:
                        if st.button("❌ Reject & Re-clear", key=f"mr_rej_{it['task_id']}", type="secondary", use_container_width=True):
                            db_act = SessionLocal()
                            try:
                                t_db = db_act.query(Task).filter(Task.id == it["task_id"]).first()
                                if t_db:
                                    t_db.status = "in_progress"
                                    if t_db.submissions:
                                        t_db.submissions[-1].verification_status = "rejected"
                                        t_db.submissions[-1].reviewed_by = officer_name
                                        t_db.submissions[-1].reviewed_at = datetime.utcnow()
                                    db_act.add(AuditLog(
                                        user=officer_name,
                                        action="manual_review_rejected",
                                        entity="task",
                                        entity_id=t_db.id,
                                    ))
                                    db_act.commit()
                                st.toast(f"Rejected! Task {it['task_id'][:6]} returned to worker for re-clearance.")
                                st.rerun()
                            finally:
                                db_act.close()

                st.write("")
    finally:
        db.close()


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


def _get_job_keyframes(item_or_job_id: Any = None) -> List[Dict[str, Any]]:
    """Return keyframes for the selected incident's video, preserving the actual annotated frame and caching extracted images."""
    from app.core.evidence import extract_frame_at_timestamp
    import cv2

    item = item_or_job_id if isinstance(item_or_job_id, dict) else {}
    filename = item.get("filename") or "pond_garbage_clean2.mp4"
    job_id = item.get("job_id") or "default"
    main_ts = item.get("video_ts", "00:05")
    photo_path = item.get("photo")
    annotated_path = item.get("annotated_path") or photo_path
    raw_path = item.get("raw_path")
    subtype = item.get("subtype", "dump_pile")
    sev = item.get("severity", 5)

    res: List[Dict[str, Any]] = []

    vid_path = item.get("video_path")
    if not vid_path and filename:
        for candidate in [
            Path("data/uploads") / filename,
            Path("data/evidence") / job_id / f"surveillance_{job_id}_annotated.mp4",
            Path(filename),
        ]:
            if candidate.is_file():
                vid_path = str(candidate)
                break

    cache_dir = Path("data/evidence") / job_id
    cache_dir.mkdir(parents=True, exist_ok=True)

    if vid_path and Path(vid_path).is_file():
        try:
            cap = cv2.VideoCapture(vid_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 100
            duration = max(3.0, total_frames / fps)
            cap.release()

            try:
                parts = main_ts.split(":")
                main_sec = float(parts[-2]) * 60 + float(parts[-1]) if len(parts) >= 2 else float(parts[0])
            except Exception:
                main_sec = 2.0
            main_sec = min(duration - 0.5, max(0.5, main_sec))

            raw_secs = [
                max(1.0, duration * 0.15),
                main_sec,
                max(2.0, duration * 0.55),
                max(3.0, duration * 0.85),
            ]
            unique_secs = sorted(list({round(s, 1) for s in raw_secs}))
            while len(unique_secs) < 4:
                unique_secs.append(min(duration - 0.5, unique_secs[-1] + 1.5))

            for s in unique_secs[:4]:
                ts_str = f"{int(s // 60):02d}:{int(s % 60):02d}"
                is_main = abs(s - main_sec) < 1.0

                frame_file = cache_dir / f"keyframe_{int(s // 60):02d}_{int(s % 60):02d}.jpg"
                if not frame_file.is_file():
                    frame_mat = extract_frame_at_timestamp(vid_path, s)
                    if frame_mat is not None:
                        cv2.imwrite(str(frame_file), frame_mat)

                kf_path = str(frame_file) if frame_file.is_file() else None
                if is_main and annotated_path and Path(annotated_path).is_file():
                    kf_path = annotated_path

                b64_val = _img_to_b64(kf_path)

                res.append({
                    "ts": ts_str,
                    "seconds": s,
                    "path": kf_path or photo_path,
                    "raw_path": str(frame_file) if frame_file.is_file() else raw_path,
                    "annotated_path": annotated_path if is_main else None,
                    "b64": b64_val or "",
                    "is_main": is_main,
                    "subtype": subtype,
                    "severity": sev,
                })
        except Exception:
            pass

    if not res:
        res.append({
            "ts": main_ts,
            "seconds": 5.0,
            "path": annotated_path or photo_path,
            "raw_path": raw_path,
            "annotated_path": annotated_path,
            "b64": _img_to_b64(annotated_path or photo_path) or "",
            "is_main": True,
            "subtype": subtype,
            "severity": sev,
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

                if is_car_or_bike(v.vehicle_type) and v.plate_text:
                    p_analysis = analyze_plate_text(v.plate_text)
                    st.markdown(render_hsrp_badge_html(v.plate_text), unsafe_allow_html=True)
                    st.markdown(
                        f'<div style="font-size:12px;color:#475569;background:#F8FAFC;border:1px solid #E2E8F0;padding:6px 10px;border-radius:6px;margin:4px 0 10px 0;">'
                        f'<b>Plate Diagnostic:</b> {escape(p_analysis["summary"])}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

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

            if item.get("plate_text"):
                p_analysis = analyze_plate_text(item["plate_text"])
                st.markdown(render_hsrp_badge_html(item["plate_text"]), unsafe_allow_html=True)
                st.markdown(
                    f'<div style="font-size:12px;color:#334155;background:#F8FAFC;border:1px solid #E2E8F0;padding:6px 10px;border-radius:6px;margin:4px 0 8px 0;">'
                    f'<b>Plate Diagnostic:</b> {escape(p_analysis["summary"])}'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if Path("data/sample_crops/plate_mh12qx4821.jpg").is_file():
                    with st.expander("Detected number plate photo", expanded=True):
                        st.image("data/sample_crops/plate_mh12qx4821.jpg", caption=f"Zoomed Plate ({item['plate_text']})", use_container_width=True)

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
        f1, _ = st.columns([1.2, 3], vertical_alignment="bottom")
        source = f1.selectbox("Source", ["All sources", "CCTV only", "Sensor reports only"], label_visibility="collapsed")
        shown = [
            i for i in incidents
            if source == "All sources" or (source == "CCTV only") == (i["source"] == "cctv")
        ]
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


def render_priority_queue_and_interventions():
    """Redesigned master-detail priority queue with key frames, filmstrip, and dispatch."""
    operations = init_operations_state()
    incidents = open_incidents()
    db = SessionLocal()
    try:
        pending_count = len(_pending_violations(db))
        mr_items = _manual_review_items(db)
        mr_count = len(mr_items)
    finally:
        db.close()
    available_leads = get_available_leads()
    with_photos = sum(1 for i in incidents if i["photo"])
    crit_count = sum(1 for i in incidents if i["severity"] >= 5)

    # -------------------------------------------------------------
    # Page Header matching docs/queue_design.png
    # -------------------------------------------------------------
    st.markdown(
        """
        <div class="fg-pq-title-group">
            <div class="fg-eyebrow">OPERATIONS</div>
            <h1>Priority queue</h1>
            <p>Every hazard the LLM model finds in CCTV video lands here with its key frame. Review, dispatch workers, and verify site clearance.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
                <div class="fg-pq-kpi-label">Awaiting review</div>
                <div class="fg-pq-kpi-val">{mr_count:02d}</div>
                <div class="fg-pq-kpi-note">worker proofs to verify</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""
            <div class="fg-pq-kpi fg-pq-kpi-4">
                <div class="fg-pq-kpi-label">Violations to review</div>
                <div class="fg-pq-kpi-val">{pending_count:02d}</div>
                <div class="fg-pq-kpi-note">dumping events to approve</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # -------------------------------------------------------------
    # Unified Tabs & Filter Control Strip
    # -------------------------------------------------------------
    c_tabs, c_sev, c_src, c_zone, c_sort, c_search = st.columns(
        [3.6, 1.1, 1.1, 1.0, 1.2, 2.0],
        vertical_alignment="center",
        gap="small",
    )

    tab_opts = [
        f"Open incidents · {len(incidents)}",
        f"Awaiting verification · {mr_count}",
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
    if "Awaiting verification" in (active_tab or ""):
        st.markdown(section_title(
            "Worker task submissions awaiting review",
            "Borderline photo clarity or clearance proofs that reached the attempt limit. Review before/after proof and approve or reject.",
        ), unsafe_allow_html=True)
        render_manual_review_tab()
        return

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
                if is_active:
                    st.markdown('<div class="fg-pq-active-banner">▶ Viewing in Frame Inspector</div>', unsafe_allow_html=True)

                col_thumb, col_body = st.columns([1.0, 2.3], gap="small")

                with col_thumb:
                    photo_file = item.get("photo")
                    if photo_file and Path(str(photo_file)).is_file():
                        st.image(photo_file, use_container_width=True)
                    else:
                        st.markdown(_render_thumb_html(item), unsafe_allow_html=True)

                with col_body:
                    worker_pill = (
                        f'<span style="background:#E0F2FE; color:#0369A1; border:1px solid #BAE6FD; font-size:10.5px; font-weight:600; padding:2px 7px; border-radius:4px;">👤 {escape(item["assigned_worker"])} &bull; {escape(item["task_status"].replace("_", " ").title())}</span>'
                        if item.get("assigned_worker")
                        else '<span style="background:#FEF3C7; color:#B45309; border:1px solid #FDE68A; font-size:10.5px; font-weight:600; padding:2px 7px; border-radius:4px;">⚠️ Unassigned</span>'
                    )

                    st.markdown(
                        f"""
                        <div class="fg-pq-meta-row">
                            <div class="fg-pq-badges">
                                <span class="fg-pq-sev-badge {sev_class}">Severity {sev}/5</span>
                                <span class="{src_class}">{escape(cam_label)}</span>
                                {worker_pill}
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
                        st.session_state[f"detail_ts_{item['id']}"] = item["video_ts"]
                        st.rerun()

                    st.markdown(
                        f"""<div class="fg-pq-desc">{escape(item['description'])}</div>""",
                        unsafe_allow_html=True,
                    )

                    # Telemetry Row
                    c_ring, c_meta1, c_meta2 = st.columns(
                        [0.6, 2.0, 2.0],
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

                # Action button to inspect frames on right side
                if is_active:
                    st.button("🔍 Active in Inspector", key=f"sel_btn_{item['key']}", type="primary", use_container_width=True, disabled=True)
                else:
                    if st.button("🔍 Inspect Frames & Evidence →", key=f"sel_btn_{item['key']}", use_container_width=True):
                        st.session_state["queue_selected"] = item["id"]
                        st.session_state[f"detail_ts_{item['id']}"] = item["video_ts"]
                        st.rerun()

    # =============================================================
    # RIGHT COLUMN: Sticky Detail Panel & Frame Inspector
    # =============================================================
    with detail_col:
        with st.container(key="fg_pq_detail_container"):
            det_sev = selected_item["severity"]
            det_sev_class = "fg-pq-sev-5" if det_sev >= 5 else ("fg-pq-sev-4" if det_sev >= 4 else "fg-pq-sev-3")
            cam_str = selected_item.get("camera") or "CAM-PUNE-01"

            st.markdown(
                f"""
                <div class="fg-pq-detail-head">
                    <div>
                        <div class="fg-pq-detail-meta">{escape(selected_item['id'])} &middot; {escape(cam_str)} &middot; {escape(selected_item.get('reported_at', ''))}</div>
                        <h2 class="fg-pq-detail-title">{escape(selected_item['location'])}</h2>
                    </div>
                    <span class="fg-pq-sev-badge {det_sev_class}">Severity {det_sev}/5</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Retrieve keyframes for this incident
            keyframes = _get_job_keyframes(selected_item)
            active_ts_key = f"detail_ts_{selected_item['id']}"
            if active_ts_key not in st.session_state:
                st.session_state[active_ts_key] = selected_item["video_ts"]

            active_ts = st.session_state.get(active_ts_key, selected_item["video_ts"])
            active_frame = next((kf for kf in keyframes if kf["ts"] == active_ts), keyframes[0] if keyframes else None)

            # Inspection Mode Switcher: Frame Inspector vs Video vs Crops
            view_modes = ["📸 Frame Inspector"]
            if selected_item.get("video_path") and Path(str(selected_item["video_path"])).is_file():
                view_modes.append("📹 Surveillance Video")
            if selected_item.get("crops"):
                view_modes.append(f"🎯 Suspect & Crops ({len(selected_item['crops'])})")

            active_mode = view_modes[0]
            if len(view_modes) > 1:
                active_mode = st.radio(
                    "Inspection Mode",
                    view_modes,
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"pq_view_mode_{selected_item['id']}",
                )

            if active_mode == "📹 Surveillance Video" and selected_item.get("video_path"):
                st.markdown(
                    f"""
                    <div class="fg-pq-chips-bar">
                        <span class="fg-pq-meta-chip">📹 Surveillance Video</span>
                        <span class="fg-pq-meta-chip">📁 {escape(selected_item.get('filename', 'video.mp4'))}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.video(str(selected_item["video_path"]))
                st.caption(f"Surveillance footage from {cam_str} with YOLOE object tracking overlays.")

            elif active_mode.startswith("🎯 Suspect & Crops") and selected_item.get("crops"):
                st.markdown(
                    """
                    <div class="fg-pq-chips-bar">
                        <span class="fg-pq-meta-chip">👤 Detected Suspects & Vehicles</span>
                        <span class="fg-pq-meta-chip">Bystanders Blurred for Privacy</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                crop_cols = st.columns(min(3, len(selected_item["crops"])), gap="small")
                for c_idx, c_info in enumerate(selected_item["crops"]):
                    with crop_cols[c_idx % len(crop_cols)]:
                        st.image(c_info["path"], caption=c_info["label"], use_container_width=True)

            else:
                # 📸 Frame Inspector Mode
                has_both = bool(selected_item.get("annotated_path") and selected_item.get("raw_path"))
                col_ov1, col_ov2 = st.columns([1.6, 1.4], vertical_alignment="center")
                with col_ov1:
                    overlay_type = "Annotated (AI Boxes)"
                    if has_both:
                        overlay_type = st.radio(
                            "Layer",
                            ["Annotated (AI Boxes)", "Raw Scene"],
                            horizontal=True,
                            label_visibility="collapsed",
                            key=f"overlay_opt_{selected_item['id']}_{active_ts}",
                        )
                with col_ov2:
                    st.markdown(
                        f"""
                        <div style="text-align:right; font-family:var(--fg-font-mono); font-size:12px; color:#0E7C86; font-weight:700;">
                            ⏱ Timestamp: {escape(active_ts)}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Determine image to render
                display_img = None
                if active_frame:
                    if overlay_type == "Raw Scene" and active_frame.get("raw_path") and Path(str(active_frame["raw_path"])).is_file():
                        display_img = active_frame["raw_path"]
                    elif active_frame.get("annotated_path") and Path(str(active_frame["annotated_path"])).is_file():
                        display_img = active_frame["annotated_path"]
                    elif active_frame.get("path") and Path(str(active_frame["path"])).is_file():
                        display_img = active_frame["path"]
                    elif active_frame.get("b64"):
                        display_img = active_frame["b64"]

                if not display_img:
                    display_img = selected_item.get("photo")

                caption_text = f"{selected_item['subtype'].replace('_', ' ').capitalize()} · Sev {selected_item['severity']}/5 · {selected_item['filename']} at {active_ts}"

                if display_img:
                    st.image(display_img, caption=caption_text, use_container_width=True)
                else:
                    st.markdown('<div class="fg-pq-hatched">No frame available for this timestamp</div>', unsafe_allow_html=True)

                # Filmstrip Multi-frame Timeline Row
                if len(keyframes) >= 2:
                    st.markdown(
                        f"""
                        <div class="fg-pq-filmstrip-wrapper">
                            <div class="fg-pq-filmstrip-head">
                                <span class="fg-pq-filmstrip-title">🎞️ Captured Keyframes ({len(keyframes)} frames across video)</span>
                                <span style="font-size:11px; color:#64748B;">Click frame to inspect</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    strip_cols = st.columns(min(4, len(keyframes)), gap="small")
                    for idx, kf in enumerate(keyframes[:4]):
                        with strip_cols[idx]:
                            is_active_kf = (kf["ts"] == active_ts)
                            thumb_path = kf.get("path") or kf.get("raw_path") or selected_item.get("photo")
                            if thumb_path and Path(str(thumb_path)).is_file():
                                st.image(str(thumb_path), use_container_width=True)
                            elif kf.get("b64"):
                                st.markdown(
                                    f'<div class="fg-pq-filmstrip-thumb {"fg-pq-filmstrip-active" if is_active_kf else ""}"><img src="{kf["b64"]}" /><div class="fg-pq-filmstrip-ts">{kf["ts"]}</div></div>',
                                    unsafe_allow_html=True,
                                )

                            btn_type = "primary" if is_active_kf else "secondary"
                            btn_label = f"● {kf['ts']}" if is_active_kf else f"{kf['ts']}"
                            if st.button(btn_label, key=f"fstrip_{selected_item['id']}_{kf['ts']}_{idx}", type=btn_type, use_container_width=True):
                                st.session_state[active_ts_key] = kf["ts"]
                                st.rerun()

            # Metadata Chips Bar
            st.markdown(
                f"""
                <div class="fg-pq-chips-bar">
                    <span class="fg-pq-meta-chip">🏷️ {escape(selected_item['subtype'])}</span>
                    <span class="fg-pq-meta-chip">🎯 Confidence: {selected_item['confidence']:.0%}</span>
                    <span class="fg-pq-meta-chip">📍 {escape(selected_item['zone'])} Zone</span>
                    <span class="fg-pq-meta-chip">🎥 {escape(selected_item.get('filename', 'video.mp4'))}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # AI Observation Box
            st.markdown(
                f"""
                <div class="fg-pq-ai-box">
                    <div class="fg-pq-ai-text">{escape(selected_item['description'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Triplet Metrics Row
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

            # Field Worker Assignment
            st.markdown(
                f"""
                <div class="fg-pq-sec-lbl">Assign Field Worker</div>
                """,
                unsafe_allow_html=True,
            )

            # Check if task is already assigned
            if selected_item.get("assigned_worker"):
                st.markdown(
                    f"""
                    <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px; padding:10px 12px; margin-bottom:10px;">
                        <div style="font-size:11px; color:#166534; font-weight:700; text-transform:uppercase;">Assigned Field Personnel</div>
                        <div style="font-size:14px; font-weight:700; color:#0F172A; margin-top:2px;">
                            👤 {escape(selected_item['assigned_worker'])} &bull; <span style="text-transform:uppercase; color:#0E7C86; font-size:12px;">{escape(selected_item['task_status'].replace('_', ' '))}</span>
                        </div>
                        <div style="font-size:12px; color:#475569; margin-top:4px;">
                            <b>Instructions:</b> {escape(selected_item.get('task_instructions') or 'Standard clearance')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                reassign_expanded = False
            else:
                reassign_expanded = True

            with st.expander("Assign / Reassign Field Worker", expanded=reassign_expanded):
                db_w = SessionLocal()
                try:
                    active_workers = db_w.query(Worker).filter(Worker.active == True).order_by(Worker.name).all()
                    worker_map = {f"{w.name} ({w.zone} Zone · {w.phone})": w for w in active_workers}
                finally:
                    db_w.close()

                if worker_map:
                    sel_worker_str = st.selectbox("Select Worker", list(worker_map.keys()), key=f"sel_w_{selected_item['id']}")
                    instructions_input = st.text_area(
                        "Task Instructions",
                        value=selected_item.get("suggested_action") or "Clean the site, remove all waste and ensure clear drainage.",
                        key=f"inst_w_{selected_item['id']}",
                        height=70,
                    )
                    c_due, c_prio = st.columns(2)
                    with c_due:
                        due_choice = st.selectbox("Due Time", ["Within 2 hours", "Within 4 hours", "End of Day (18:00)", "Tomorrow 10:00"], key=f"due_w_{selected_item['id']}")
                    with c_prio:
                        prio_choice = st.selectbox("Priority", ["high", "critical", "medium"], key=f"prio_w_{selected_item['id']}")

                    if st.button("Assign Worker & Dispatch", key=f"btn_assign_w_{selected_item['id']}", type="primary", use_container_width=True):
                        worker_obj = worker_map[sel_worker_str]
                        now_dt = datetime.utcnow()
                        if "2 hours" in due_choice:
                            due_dt = now_dt + timedelta(hours=2)
                        elif "4 hours" in due_choice:
                            due_dt = now_dt + timedelta(hours=4)
                        elif "End of Day" in due_choice:
                            due_dt = now_dt.replace(hour=12, minute=30)
                        else:
                            due_dt = now_dt + timedelta(days=1)

                        db_assign = SessionLocal()
                        try:
                            inc_db = db_assign.query(Incident).filter(Incident.id == selected_item["incident_id"]).first()
                            if inc_db:
                                inc_db.status = "assigned"

                            task_id = generate_uuid()
                            new_task = Task(
                                id=task_id,
                                incident_id=selected_item["incident_id"],
                                worker_id=worker_obj.id,
                                assigned_by=st.session_state.get("reviewing_officer", "Duty Officer"),
                                assigned_at=now_dt,
                                due_at=due_dt,
                                priority=prio_choice,
                                instructions=instructions_input,
                                status="assigned",
                            )
                            db_assign.add(new_task)
                            db_assign.flush()
                            db_assign.add(AuditLog(
                                user=st.session_state.get("reviewing_officer", "Duty Officer"),
                                action="assigned_worker",
                                entity="task",
                                entity_id=task_id,
                            ))
                            db_assign.commit()
                            db_assign.refresh(new_task)
                            send_task_assignment_alert(db_assign, new_task)
                            st.toast(f"Assigned to {worker_obj.name}! Alert dispatched.")
                            st.rerun()
                        finally:
                            db_assign.close()
                else:
                    st.warning("No active field workers registered. Run seed script first.")

            # Resolve Rule: Verified or Admin Override
            st.markdown('<div class="fg-pq-sec-lbl" style="margin-top:14px;">Resolution Status</div>', unsafe_allow_html=True)
            if selected_item.get("task_status") == "verified":
                st.success("✅ Work verified by Municipal AI Verification Engine. Incident resolved.")
            else:
                with st.expander("Admin Override & Manual Resolution"):
                    st.caption("Incidents are normally resolved automatically upon AI photo verification. You may authorize resolution manually with reason.")
                    override_officer = st.text_input("Authorizing Officer Name", value=st.session_state.get("reviewing_officer", "Duty Officer"), key=f"ov_off_{selected_item['id']}")
                    override_reason = st.text_input("Reason for Override (Required)", placeholder="e.g. Visual clearance confirmed via CCTV zoom feed", key=f"ov_rsn_{selected_item['id']}")
                    if st.button("Authorize Override & Mark Resolved", key=f"ov_btn_{selected_item['id']}", type="secondary", disabled=not bool(override_reason.strip())):
                        _resolve_incident(selected_item["incident_id"], officer=f"{override_officer} (Override: {override_reason})")
                        st.toast(f"Incident {selected_item['id']} marked resolved via admin override.")
                        st.rerun()


def render_priority_queue():
    """Alias for unified view."""
    render_priority_queue_and_interventions()
