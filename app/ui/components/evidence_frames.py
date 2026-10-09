"""Key evidence frames saved by the video pipeline, shared by the CCTV page and the queue."""

from pathlib import Path
from typing import List, Optional, Tuple

import streamlit as st
from sqlalchemy.orm import Session

from app.db.models import Incident, Job
from app.ui.components.styles import icon

INCIDENT_FRAME_KINDS = ("annotated", "frame")


def incident_frame(inc: Incident) -> Optional[str]:
    """The annotated key frame for an incident (falls back to the raw frame)."""
    for kind in INCIDENT_FRAME_KINDS:
        path = next((e.path for e in inc.evidences if e.kind == kind and Path(e.path).is_file()), None)
        if path:
            return path
    return None


def job_key_frames(job: Job) -> List[Tuple[str, str]]:
    """(path, caption) for every incident key frame in a job, most severe first."""
    frames = []
    for inc in sorted(job.incidents, key=lambda i: -i.severity):
        path = incident_frame(inc)
        if path:
            frames.append((path, f"{inc.subtype.replace('_', ' ').capitalize()} at {inc.video_ts} · severity {inc.severity}/5"))
    return frames


def latest_job_for_video(db: Session, filename: str) -> Optional[Job]:
    if not filename:
        return None
    return (
        db.query(Job)
        .filter(Job.filename == filename, Job.status == "completed")
        .order_by(Job.created_at.desc())
        .first()
    )


def render_frame_gallery(frames: List[Tuple[str, str]], key: str, columns: int = 3) -> None:
    """Fixed-aspect thumbnail grid of evidence frames with captions."""
    if not frames:
        st.markdown(f'<div class="fg-noframe">{icon("camera", 20)}No key frames saved</div>', unsafe_allow_html=True)
        return
    cols = st.columns(columns)
    for i, (path, caption) in enumerate(frames):
        with cols[i % columns]:
            with st.container(key=f"fgframe_{key}_{i}"):
                st.image(path, caption=caption, use_container_width=True)
