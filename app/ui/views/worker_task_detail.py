"""Worker app: Task Detail & AI Work Verification view for field workers."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import streamlit as st
from sqlalchemy.orm import joinedload

from app.config import settings
from app.core.verify_work import verify_and_record_submission
from app.db.models import Incident, Task, TaskSubmission, Worker
from app.db.session import SessionLocal
from app.ui.components.styles import _flat, icon, section_title, status_pill
from app.ui.pune_data import PUNE_LOCATIONS, location_for_job


def _load_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Load complete task data including incident, evidences, and past submissions."""
    db = SessionLocal()
    try:
        task = (
            db.query(Task)
            .options(
                joinedload(Task.incident).joinedload(Incident.evidences),
                joinedload(Task.incident).joinedload(Incident.job),
                joinedload(Task.submissions),
                joinedload(Task.worker),
            )
            .filter(Task.id == task_id)
            .first()
        )
        if not task:
            return None

        inc = task.incident
        loc = location_for_job(inc.job.filename, inc.job.source_gps) if inc.job else PUNE_LOCATIONS[0]

        before_photo = None
        for ev in inc.evidences:
            if ev.kind in ("annotated", "frame") and Path(ev.path).is_file():
                before_photo = ev.path
                break

        subs = []
        for s in sorted(task.submissions, key=lambda x: x.attempt_number):
            reasons = []
            if s.rejection_reasons:
                try:
                    import json
                    reasons = json.loads(s.rejection_reasons) if isinstance(s.rejection_reasons, str) and s.rejection_reasons.startswith("[") else [s.rejection_reasons]
                except Exception:
                    reasons = [str(s.rejection_reasons)]
            subs.append({
                "id": s.id,
                "attempt_number": s.attempt_number,
                "photo_path": s.after_photo_path,
                "status": s.verification_status,
                "submitted_at": s.submitted_at,
                "ai_confidence": s.gemini_confidence,
                "garbage_remaining_pct": s.yoloe_garbage_after_pct,
                "rejection_reasons": reasons,
                "notes": s.worker_notes,
                "feedback": s.gemini_reason,
            })

        return {
            "id": task.id,
            "incident_id": inc.id,
            "type": inc.type,
            "subtype": inc.subtype.replace("_", " ").title(),
            "severity": inc.severity,
            "location": loc["name"],
            "zone": loc.get("zone", "Central"),
            "lat": loc.get("lat"),
            "lon": loc.get("lon"),
            "description": inc.description,
            "assigned_at": task.assigned_at,
            "due_at": task.due_at,
            "priority": task.priority,
            "instructions": task.instructions or "Clean the site, remove all waste and ensure clear drainage.",
            "status": task.status,
            "worker_name": task.worker.name if task.worker else "Assigned Worker",
            "before_photo": before_photo,
            "submissions": subs,
            "attempts_count": len(subs),
        }
    finally:
        db.close()


def render_worker_task_detail_view() -> None:
    """Desktop view for reviewing hazard details and submitting work proof."""
    task_id = st.session_state.get("worker_active_task_id")
    worker_id = st.session_state.get("worker_id")

    if not task_id:
        st.warning("No task selected.")
        if st.button("← Back to My Tasks", key="wtd_back_empty"):
            st.session_state["active_worker_page"] = "worker-tasks"
            st.rerun()
        return

    task = _load_task(task_id)
    if not task:
        st.error(f"Task {task_id} not found.")
        if st.button("← Back to My Tasks", key="wtd_back_notfound"):
            st.session_state["active_worker_page"] = "worker-tasks"
            st.rerun()
        return

    # Top action bar / Breadcrumbs
    col_back, col_badge = st.columns([4, 1], vertical_alignment="center")
    with col_back:
        if st.button("← Back to My Tasks", key="wtd_back_btn", type="secondary"):
            st.session_state["active_worker_page"] = "worker-tasks"
            st.rerun()
    with col_badge:
        st_color = "#0E7C86" if task["status"] == "verified" else ("#D97706" if task["status"] == "manual_review" else "#EA580C")
        st.markdown(
            f"""
            <div style="text-align:right;">
                <span style="background:{st_color}18; color:{st_color}; border:1px solid {st_color}40; font-size:12px; font-weight:700; padding:4px 10px; border-radius:6px; text-transform:uppercase;">
                    {task['status'].replace('_', ' ')}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Title header
    st.markdown(
        f"""
        <div class="fg-pq-title-group" style="margin-top:10px;">
            <div class="fg-eyebrow">TASK DISPATCH #{task['id'][:8].upper()} &bull; {task['zone'].upper()} ZONE</div>
            <h1>{task['location']} &bull; {task['subtype']}</h1>
            <p>Assigned to <b>{task['worker_name']}</b> &bull; Priority: <b style="text-transform:uppercase;">{task['priority']}</b> &bull; Due: <b>{task['due_at'].strftime('%d %b, %H:%M IST') if task['due_at'] else 'Within 2 hours'}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Main 2-Column desktop layout matching design images
    col_left, col_right = st.columns([1, 1.15], gap="large")

    # LEFT COLUMN: Before Proof & Incident Details
    with col_left:
        st.markdown(
            """
            <div style="font-family:var(--fg-font-head); font-size:16px; font-weight:700; color:#0F172A; margin-bottom:10px;">
                1. Initial Incident & Site Assessment
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container():
            if task["before_photo"] and Path(task["before_photo"]).is_file():
                st.image(task["before_photo"], caption=f"Reported Condition (Severity {task['severity']}/5)", use_container_width=True)
            else:
                st.markdown('<div class="fg-pq-hatched" style="height:240px;">Hazard evidence still unavailable</div>', unsafe_allow_html=True)

            st.markdown(
                f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:14px; margin-top:12px;">
                    <div style="font-size:12px; font-weight:700; color:#64748B; text-transform:uppercase; margin-bottom:4px;">Supervisor Directives</div>
                    <div style="font-size:13.5px; color:#0F172A; font-weight:500; margin-bottom:12px;">
                        {task['instructions']}
                    </div>
                    <div style="font-size:12px; font-weight:700; color:#64748B; text-transform:uppercase; margin-bottom:4px;">Incident Description</div>
                    <div style="font-size:13px; color:#334155; margin-bottom:12px;">
                        {task['description']}
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:12px; color:#64748B; font-family:var(--fg-font-mono); border-top:1px solid #E2E8F0; pt:8px; padding-top:8px;">
                        <span>GPS: {f"{task['lat']:.4f}" if task.get('lat') is not None else "18.5204"}, {f"{task['lon']:.4f}" if task.get('lon') is not None else "73.8567"}</span>
                        <span>Severity: {task['severity']}/5</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # RIGHT COLUMN: Work Proof Submission & AI Verification Engine
    with col_right:
        st.markdown(
            """
            <div style="font-family:var(--fg-font-head); font-size:16px; font-weight:700; color:#0F172A; margin-bottom:10px;">
                2. Live Proof Submission & AI Verification
            </div>
            """,
            unsafe_allow_html=True,
        )

        latest_sub = task["submissions"][-1] if task["submissions"] else None

        # State A: Already Verified
        if task["status"] == "verified":
            st.success("🎉 Site Clearance Verified! Incident has been resolved and closed.")
            if latest_sub and latest_sub["photo_path"] and Path(latest_sub["photo_path"]).is_file():
                st.image(latest_sub["photo_path"], caption=f"Verified Completion Proof (Attempt {latest_sub['attempt_number']})", use_container_width=True)

            ai_conf = latest_sub.get("ai_confidence") or 0.95
            rem_pct = latest_sub.get("garbage_remaining_pct") or 0.0
            st.markdown(
                f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:12px; margin-top:8px;">
                    <div style="font-size:13px; font-weight:700; color:#166534;">Municipal AI Audit Report</div>
                    <div style="font-size:12px; color:#14532D; margin-top:4px;">
                        &bull; AI Visual Confirmation: <b>{ai_conf*100:.1f}%</b><br/>
                        &bull; Garbage Area Remaining: <b>{rem_pct:.1f}%</b> (Pass threshold &le; {settings.VERIFY_MAX_GARBAGE_REMAINING_PCT}%)<br/>
                        &bull; Verified At: <b>{latest_sub['submitted_at'].strftime('%Y-%m-%d %H:%M IST') if latest_sub['submitted_at'] else 'Recently'}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # State B: Under Manual Review
        elif task["status"] == "manual_review":
            st.warning("⚠️ Task Escalated to Supervisor for Manual Review")
            st.info(
                "3 verification attempts were submitted without conclusive clearance, or borderline image conditions occurred. "
                "The zonal supervisor has been alerted and will inspect the before/after photos manually in the console."
            )
            if latest_sub and latest_sub["photo_path"] and Path(latest_sub["photo_path"]).is_file():
                st.image(latest_sub["photo_path"], caption="Latest Submitted Photo under Supervisor Review", use_container_width=True)

        # State C: Pending or In Progress (Allows submission)
        else:
            attempts_left = max(0, settings.VERIFY_MAX_ATTEMPTS - task["attempts_count"])
            
            # Show guidance if previous attempt was rejected
            if latest_sub and latest_sub["status"] == "rejected":
                st.error(
                    f"⚠️ Attempt {latest_sub['attempt_number']} of {settings.VERIFY_MAX_ATTEMPTS} was rejected by the verification engine.\n\n"
                    f"**Reason:** {', '.join(latest_sub['rejection_reasons']) or 'Garbage or blockage still visible in the site photo.'}\n\n"
                    f"**Guidance:** Please ensure the area is thoroughly cleared, stand at the same vantage point as the before photo, and take a bright, steady shot. You have {attempts_left} attempt(s) remaining."
                )

            st.markdown(
                f"""
                <div style="background:#EFF6FF; border:1px solid #DBEAFE; border-radius:6px; padding:10px 12px; font-size:12px; color:#1E40AF; margin-bottom:12px;">
                    📸 <b>Proof of Clearance Required:</b> Take a photo from the same location showing the drain/culvert completely cleared. Attempt <b>{task['attempts_count'] + 1} of {settings.VERIFY_MAX_ATTEMPTS}</b>.
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Camera input with uploader fallback
            camera_img = st.camera_input("Capture live site photo", key=f"cam_input_{task['id']}")
            file_img = st.file_uploader(
                "Or choose photo from device",
                type=["jpg", "jpeg", "png"],
                key=f"file_input_{task['id']}",
                help="Accepts high-resolution JPG or PNG format",
            )

            chosen_file = camera_img if camera_img is not None else file_img

            st.markdown(
                """
                <div style="font-size:13px; font-weight:700; color:#0F172A; margin-top:6px; margin-bottom:6px;">
                    📋 Site Clearance Report & Notes
                </div>
                """,
                unsafe_allow_html=True,
            )

            c_f1, c_f2 = st.columns(2)
            with c_f1:
                action_taken = st.selectbox(
                    "Primary Clearance Action",
                    [
                        "Solid waste & dump pile hauled away",
                        "De-silted & dredged storm drain",
                        "Culvert flap gate unblocked",
                        "High pressure silt jetting performed",
                        "Surface drainage water cleared",
                    ],
                    key=f"w_act_{task['id']}",
                )
            with c_f2:
                waste_qty = st.selectbox(
                    "Waste Bags / Volume Cleared",
                    [
                        "1-2 Bags (~15 kg waste)",
                        "3-5 Bags (~40 kg waste)",
                        "6-10 Bags (~80 kg waste)",
                        "Heavy truckload / bulky debris",
                        "Silt & sediment only",
                    ],
                    key=f"w_qty_{task['id']}",
                )

            c_f3, c_f4 = st.columns(2)
            with c_f3:
                flow_status = st.selectbox(
                    "Drain Flow State",
                    [
                        "Flowing freely without backlog",
                        "Water receding steadily",
                        "Dry culvert / no standing water",
                        "Minor dampness / slow drainage",
                    ],
                    key=f"w_flow_{task['id']}",
                )
            with c_f4:
                equipment_used = st.selectbox(
                    "Equipment / Tools Utilized",
                    [
                        "Manual spades, rakes & PMC sacks",
                        "Jetting suction hose & municipal tanker",
                        "Excavator backhoe & dumper truck",
                        "Safety suits, hooks & silt buckets",
                    ],
                    key=f"w_eq_{task['id']}",
                )

            remarks = st.text_input(
                "Worker Remarks / Observations",
                placeholder="e.g. Cleared all plastic bottles, sediment scooped out, drain mouth unobstructed",
                key=f"notes_input_{task['id']}",
            )

            full_notes = f"Action: {action_taken} | Waste: {waste_qty} | Flow: {flow_status} | Tools: {equipment_used} | Remarks: {remarks.strip() or 'Site cleared'}"

            btn_submit = st.button(
                "🚀 Run AI Work Verification",
                type="primary",
                use_container_width=True,
                disabled=(chosen_file is None),
                key=f"submit_verify_{task['id']}",
            )

            if btn_submit and chosen_file is not None:
                with st.spinner("Analyzing site clearance photo with Gemini VLM & YOLOE..."):
                    # Save after photo
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    attempt_no = task["attempts_count"] + 1
                    filename = f"task_{task['id'][:8]}_attempt_{attempt_no}_{timestamp}.jpg"
                    dest_path = settings.AFTER_PHOTOS_DIR / filename
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(dest_path, "wb") as f:
                        f.write(chosen_file.getbuffer())

                    # Call 6-step verification engine
                    db = SessionLocal()
                    try:
                        submission = verify_and_record_submission(
                            db=db,
                            task_id=task["id"],
                            after_image_input=dest_path,
                            proof_lat=task.get("lat"),
                            proof_lng=task.get("lon"),
                            worker_notes=full_notes,
                        )
                        v_status = submission.verification_status
                    finally:
                        db.close()

                    if v_status == "verified":
                        st.toast("Work verified successfully! Incident marked resolved.", icon="✅")
                    elif v_status == "manual_review":
                        st.toast("Escalated to supervisor for manual review.", icon="⚠️")
                    else:
                        st.toast("Verification rejected. Check reasons and retake photo.", icon="❌")

                    st.rerun()

    # Submissions Audit Trail
    if task["submissions"]:
        st.write("")
        st.markdown(
            """
            <div style="font-family:var(--fg-font-head); font-size:15px; font-weight:700; color:#0F172A; margin-top:20px; margin-bottom:10px;">
                Verification Attempts Log
            </div>
            """,
            unsafe_allow_html=True,
        )

        for s in reversed(task["submissions"]):
            s_color = "#0E7C86" if s["status"] == "verified" else ("#D97706" if s["status"] == "manual_review" else "#EA580C")
            with st.container():
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:10px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-weight:700; font-size:13px; color:#0F172A;">Attempt #{s['attempt_number']}</span>
                            <span style="font-size:12px; color:#64748B; margin-left:8px;">{s['submitted_at'].strftime('%H:%M:%S IST, %d %b') if s['submitted_at'] else ''}</span>
                            <div style="font-size:12px; color:#475569; margin-top:2px;">
                                {s.get('feedback') or 'Evaluated against municipal drainage cleanliness standards.'}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <span style="background:{s_color}18; color:{s_color}; border:1px solid {s_color}40; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px; text-transform:uppercase;">
                                {s['status'].replace('_', ' ')}
                            </span>
                            <div style="font-size:11px; color:#64748B; font-family:var(--fg-font-mono); margin-top:4px;">
                                Garbage: {s.get('garbage_remaining_pct', 0.0):.1f}%
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
