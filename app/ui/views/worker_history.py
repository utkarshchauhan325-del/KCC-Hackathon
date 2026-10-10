"""Worker app: Task History & Completed Clearance Proofs view."""

from pathlib import Path
from typing import Any, Dict, List
import streamlit as st
from sqlalchemy.orm import joinedload

from app.db.models import Incident, Task, TaskSubmission
from app.db.session import SessionLocal
from app.ui.components.styles import _flat, icon, section_title, status_pill
from app.ui.pune_data import PUNE_LOCATIONS, location_for_job


def _worker_history_tasks(worker_id: str) -> List[Dict[str, Any]]:
    """Retrieve completed & verified tasks for a given worker."""
    db = SessionLocal()
    try:
        tasks = (
            db.query(Task)
            .options(
                joinedload(Task.incident).joinedload(Incident.evidences),
                joinedload(Task.incident).joinedload(Incident.job),
                joinedload(Task.submissions),
            )
            .filter(Task.worker_id == worker_id, Task.status == "verified")
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

            verified_sub = None
            for s in reversed(t.submissions):
                if s.verification_status == "verified":
                    verified_sub = s
                    break

            items.append({
                "id": t.id,
                "type": inc.type,
                "subtype": inc.subtype.replace("_", " ").title(),
                "severity": inc.severity,
                "location": loc["name"],
                "zone": loc.get("zone", "Central"),
                "description": inc.description,
                "assigned_at": t.assigned_at,
                "due_at": t.due_at,
                "priority": t.priority,
                "before_photo": before_photo,
                "after_photo": verified_sub.after_photo_path if verified_sub else None,
                "verified_at": verified_sub.submitted_at if verified_sub else None,
                "garbage_remaining_pct": verified_sub.yoloe_garbage_after_pct if verified_sub else 0.0,
                "ai_confidence": verified_sub.gemini_confidence if verified_sub else 0.95,
                "attempts_count": len(t.submissions),
            })
        return items
    finally:
        db.close()


def render_worker_history_view() -> None:
    """Desktop view displaying the worker's verified task history and before/after comparisons."""
    worker_id = st.session_state.get("worker_id")
    worker_name = st.session_state.get("worker_name", "Field Worker")
    worker_zone = st.session_state.get("worker_zone", "Pune")

    if not worker_id:
        st.warning("Please sign in with your authorized field worker account.")
        return

    items = _worker_history_tasks(worker_id)

    # Header
    st.markdown(
        f"""
        <div class="fg-pq-title-group">
            <div class="fg-eyebrow">FIELD RECORD &bull; {worker_zone.upper()} DIVISION</div>
            <h1>Completed & Verified Work History</h1>
            <p>Archive of all civic hazards successfully cleared by <b>{worker_name}</b> and certified by AI Work Verification.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not items:
        st.markdown(
            """
            <div class="fg-noframe" style="aspect-ratio:auto; height:180px; padding:30px; text-align:center;">
                <div style="font-size:24px; margin-bottom:8px;">📋</div>
                <div style="font-size:15px; font-weight:600; color:#0F172A;">No completed tasks yet.</div>
                <div style="font-size:13px; color:#64748B;">Once your site clearance photos are verified by AI or supervisor approval, they will appear here.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(f'<div style="font-size:13px; color:#64748B; margin-bottom:12px;">Total Verified Jobs: <b>{len(items)}</b></div>', unsafe_allow_html=True)

    for it in items:
        with st.container():
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <div>
                            <span style="font-family:var(--fg-font-head); font-size:16px; font-weight:700; color:#0F172A;">
                                {it['location']} &bull; <span style="color:#0E7C86;">{it['subtype']}</span>
                            </span>
                            <span style="font-family:var(--fg-font-mono); font-size:11px; color:#64748B; margin-left:8px;">TASK-{it['id'][:6].upper()}</span>
                        </div>
                        <span style="background:#0E7C8618; color:#0E7C86; border:1px solid #0E7C8640; font-size:11px; font-weight:700; padding:3px 8px; border-radius:6px; text-transform:uppercase;">
                            VERIFIED & RESOLVED
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Before / After side-by-side
            c_before, c_after, c_meta = st.columns([1, 1, 1.2], gap="medium")

            with c_before:
                if it["before_photo"] and Path(it["before_photo"]).is_file():
                    st.image(it["before_photo"], caption=f"Reported Hazard (Severity {it['severity']}/5)", use_container_width=True)
                else:
                    st.markdown('<div class="fg-pq-hatched" style="height:160px;">Before proof unavailable</div>', unsafe_allow_html=True)

            with c_after:
                if it["after_photo"] and Path(it["after_photo"]).is_file():
                    st.image(it["after_photo"], caption="Verified Site Clearance", use_container_width=True)
                else:
                    st.markdown('<div class="fg-pq-hatched" style="height:160px;">After proof pending</div>', unsafe_allow_html=True)

            with c_meta:
                rem_pct = it.get("garbage_remaining_pct", 0.0)
                conf = (it.get("ai_confidence") or 0.95) * 100
                st.markdown(
                    f"""
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:12px; font-size:12.5px; height:100%;">
                        <div style="font-weight:700; color:#0F172A; margin-bottom:6px;">Verification Summary</div>
                        <div style="color:#475569; margin-bottom:4px;">&bull; Date: <b>{it['verified_at'].strftime('%d %b %Y, %H:%M IST') if it['verified_at'] else 'Verified'}</b></div>
                        <div style="color:#475569; margin-bottom:4px;">&bull; AI Clearance Confidence: <b style="color:#16A34A;">{conf:.1f}%</b></div>
                        <div style="color:#475569; margin-bottom:4px;">&bull; Residual Waste: <b>{rem_pct:.1f}%</b></div>
                        <div style="color:#475569; margin-bottom:10px;">&bull; Attempts Taken: <b>{it['attempts_count']}</b></div>
                        <div style="font-size:12px; color:#64748B;">{it['description']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.write("")
