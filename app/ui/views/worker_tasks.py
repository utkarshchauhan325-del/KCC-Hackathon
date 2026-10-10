"""Worker app: My Tasks view for field workers."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import streamlit as st
from sqlalchemy.orm import joinedload

from app.db.models import Incident, Task, TaskSubmission, Worker
from app.db.session import SessionLocal
from app.ui.components.styles import _flat, icon, section_title, status_pill
from app.ui.pune_data import PUNE_LOCATIONS, location_for_job


def _worker_tasks(worker_id: str) -> List[Dict[str, Any]]:
    """Retrieve assigned tasks for a given worker."""
    db = SessionLocal()
    try:
        tasks = (
            db.query(Task)
            .options(
                joinedload(Task.incident).joinedload(Incident.evidences),
                joinedload(Task.incident).joinedload(Incident.job),
                joinedload(Task.submissions),
            )
            .filter(Task.worker_id == worker_id)
            .order_by(Task.assigned_at.desc())
            .all()
        )

        items = []
        for t in tasks:
            inc = t.incident
            loc = location_for_job(inc.job.filename, inc.job.source_gps) if inc.job else PUNE_LOCATIONS[0]
            
            # Find key evidence photo (before photo)
            before_photo = None
            for ev in inc.evidences:
                if ev.kind in ("annotated", "frame") and Path(ev.path).is_file():
                    before_photo = ev.path
                    break

            latest_sub = t.submissions[-1] if t.submissions else None

            items.append({
                "id": t.id,
                "task_id": t.id,
                "incident_id": inc.id,
                "type": inc.type,
                "subtype": inc.subtype.replace("_", " ").title(),
                "severity": inc.severity,
                "location": loc["name"],
                "zone": loc.get("zone", "Central"),
                "description": inc.description,
                "assigned_at": t.assigned_at,
                "due_at": t.due_at,
                "priority": t.priority,
                "instructions": t.instructions or "Clean the site, remove all waste and ensure clear drainage.",
                "status": t.status,
                "before_photo": before_photo,
                "attempts": len(t.submissions),
                "latest_status": latest_sub.verification_status if latest_sub else None,
            })
        return items
    finally:
        db.close()


def render_worker_tasks_view() -> None:
    """Desktop view of tasks assigned to the logged-in field worker."""
    worker_id = st.session_state.get("worker_id")
    worker_name = st.session_state.get("worker_name", "Field Worker")
    worker_zone = st.session_state.get("worker_zone", "Pune")

    if not worker_id:
        st.warning("Please sign in with your authorized field worker account.")
        return

    tasks = _worker_tasks(worker_id)
    active_tasks = [t for t in tasks if t["status"] not in ("verified",)]
    verified_tasks = [t for t in tasks if t["status"] == "verified"]

    # Header
    st.markdown(
        f"""
        <div class="fg-pq-title-group">
            <div class="fg-eyebrow">FIELD OPERATIONS &bull; {worker_zone.upper()} ZONE</div>
            <h1>My Assigned Tasks</h1>
            <p>Welcome, <b>{worker_name}</b>. Review assigned civic hazards, visit the site, and submit your completion photo for AI verification.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPI Strip
    k1, k2, k3, k4 = st.columns(4, gap="small")
    with k1:
        st.markdown(
            f"""
            <div class="fg-pq-kpi fg-pq-kpi-1">
                <div class="fg-pq-kpi-label">Active Tasks</div>
                <div class="fg-pq-kpi-val">{len(active_tasks):02d}</div>
                <div class="fg-pq-kpi-note">requiring site clearance</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        urgent_count = sum(1 for t in active_tasks if t["priority"] in ("critical", "high"))
        st.markdown(
            f"""
            <div class="fg-pq-kpi fg-pq-kpi-3">
                <div class="fg-pq-kpi-label">High Priority</div>
                <div class="fg-pq-kpi-val">{urgent_count:02d}</div>
                <div class="fg-pq-kpi-note">critical or high urgency</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        review_count = sum(1 for t in tasks if t["status"] == "manual_review")
        st.markdown(
            f"""
            <div class="fg-pq-kpi fg-pq-kpi-2">
                <div class="fg-pq-kpi-label">Under Review</div>
                <div class="fg-pq-kpi-val">{review_count:02d}</div>
                <div class="fg-pq-kpi-note">with supervisor</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""
            <div class="fg-pq-kpi fg-pq-kpi-4">
                <div class="fg-pq-kpi-label">Verified & Done</div>
                <div class="fg-pq-kpi-val">{len(verified_tasks):02d}</div>
                <div class="fg-pq-kpi-note">AI confirmed resolved</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Filter Toolbar
    f_col1, f_col2 = st.columns([3, 1], vertical_alignment="center")
    with f_col1:
        tab_opts = ["Active Tasks", "All Tasks", "Completed & Verified"]
        active_tab = st.pills("Filter", tab_opts, default=tab_opts[0], label_visibility="collapsed", key="w_task_filter")
    with f_col2:
        st.markdown(f'<div style="text-align:right; font-size:12px; color:#64748B;">Showing {len(active_tasks)} assigned</div>', unsafe_allow_html=True)

    st.write("")

    # Display list of tasks
    shown = active_tasks if active_tab == "Active Tasks" else (verified_tasks if active_tab == "Completed & Verified" else tasks)

    if not shown:
        st.markdown(
            """
            <div class="fg-noframe" style="aspect-ratio:auto; height:180px; padding:30px; text-align:center;">
                <div style="font-size:24px; margin-bottom:8px;">✅</div>
                <div style="font-size:15px; font-weight:600; color:#0F172A;">All Clear! No tasks in this view.</div>
                <div style="font-size:13px; color:#64748B;">Great work. New municipal dispatch tasks will appear here automatically.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for t in shown:
        card_class = "fg-pq-card-box"
        status_label = t["status"].replace("_", " ").title()
        badge_color = "#0E7C86" if t["status"] == "verified" else ("#D97706" if t["status"] == "manual_review" else "#EA580C")
        
        with st.container():
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span class="fg-pq-sev-badge fg-pq-sev-{min(5, max(3, t['severity']))}">Severity {t['severity']}/5</span>
                            <span style="font-family:var(--fg-font-mono); font-size:11px; color:#64748B; font-weight:600;">TASK-{t['id'][:6].upper()}</span>
                        </div>
                        <span style="background:{badge_color}18; color:{badge_color}; border:1px solid {badge_color}40; font-size:11px; font-weight:700; padding:3px 8px; border-radius:6px; text-transform:uppercase;">
                            {status_label}
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c_thumb, c_body, c_act = st.columns([1.1, 2.4, 1.2], vertical_alignment="center", gap="medium")

            with c_thumb:
                if t["before_photo"] and Path(t["before_photo"]).is_file():
                    st.image(t["before_photo"], caption="Reported Hazard (Before)", use_container_width=True)
                else:
                    st.markdown('<div class="fg-pq-hatched">No before still</div>', unsafe_allow_html=True)

            with c_body:
                st.markdown(
                    f"""
                    <div style="font-family:var(--fg-font-head); font-size:16px; font-weight:700; color:#0F172A; margin-bottom:4px;">
                        {t['location']} &bull; <span style="color:#0E7C86;">{t['subtype']}</span>
                    </div>
                    <div style="font-size:13px; color:#475569; margin-bottom:8px;">{t['description']}</div>
                    <div style="background:#F8FAFC; border-left:3px solid #0E7C86; padding:6px 10px; border-radius:4px; font-size:12px; color:#1E293B;">
                        <b>Officer Instructions:</b> {t['instructions']}
                    </div>
                    <div style="display:flex; gap:12px; margin-top:8px; font-size:11.5px; color:#64748B; font-family:var(--fg-font-mono);">
                        <span>Priority: <b>{t['priority'].upper()}</b></span>
                        <span>Due: <b>{t['due_at'].strftime('%H:%M IST') if t['due_at'] else 'Within 2h'}</b></span>
                        <span>Submissions: <b>{t['attempts']} / 3</b></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c_act:
                btn_label = "View Verified Proof →" if t["status"] == "verified" else "Open Task & Submit Proof →"
                btn_type = "secondary" if t["status"] == "verified" else "primary"
                if st.button(btn_label, key=f"btn_open_task_{t['id']}", type=btn_type, use_container_width=True):
                    st.session_state["worker_active_task_id"] = t["id"]
                    st.session_state["active_worker_page"] = "worker-task-detail"
                    st.rerun()

            st.write("")
