"""CCTV Monitoring View - Live feeds & Gemini VLM Video Ingestion."""

import json
import textwrap
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import settings
from app.ui.pune_data import CCTV_CAMERAS
from app.core.pipeline import CivicEyePipeline
from app.db.session import SessionLocal
from app.db.models import Incident, Job
from app.core.detector import CATEGORY_LABELS, WASTE_TYPE_LABELS

def render_cctv_monitoring():
    """Render 3 CCTV Camera grid & AI video inspection pipeline."""

    st.markdown(textwrap.dedent("""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>CCTV Surveillance & AI Camera Grid</h1>
            <p>Live municipal optical feeds with automated drain blockage & dumping detection</p>
        </div>
        <div class="header-actions">
            <div class="date-badge">🔴 3 Cameras Streaming (1080p 30fps)</div>
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

    tab_grid, tab_upload = st.tabs(["📹 Live Camera Grid (3 Feeds)", "🚀 Video Ingestion & AI Inspection"])

    with tab_grid:
        st.markdown("### 📡 Municipal Optical Feeds - Pune Central & Transit Corridors")

        # 1x3 Grid for Top 3 Cameras
        cols = st.columns(3)
        for col, cam in zip(cols, CCTV_CAMERAS[:3]):
            with col:
                r_col = "#DC2626" if cam["risk_level"] == "Critical" else ("#EA580C" if cam["risk_level"] == "High" else "#16A34A")

                card_html = textwrap.dedent(f"""
<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:14px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
<div>
<b style="font-size:13px; color:#0F172A;">{cam['name']}</b>
<div style="font-size:11px; color:#64748B;">{cam['id']} • Zone {cam['zone']}</div>
</div>
<span style="background:{r_col}15; color:{r_col}; font-weight:700; font-size:10px; padding:2px 8px; border-radius:10px; border:1px solid {r_col}40;">
{cam['risk_level'].upper()}
</span>
</div>
<div style="position:relative; width:100%; height:180px; background:#0B0F19; border-radius:8px; overflow:hidden; display:flex; align-items:center; justify-content:center;">
<div style="position:absolute; inset:0; opacity:0.35; background: radial-gradient(circle at 50% 50%, #334155 0%, #020617 100%);"></div>
<div style="position:absolute; top:8px; left:8px; background:rgba(0,0,0,0.65); color:#22C55E; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px; font-family:monospace;">
REC ● {cam['stream_fps']} FPS
</div>
<div style="position:absolute; top:8px; right:8px; background:rgba(0,0,0,0.65); color:#F8FAFC; font-size:10px; padding:2px 6px; border-radius:4px; font-family:monospace;">
{cam['lat']}, {cam['lng']}
</div>
<div style="position:absolute; bottom:16px; left:16px; right:16px; border:2px dashed {r_col}; background:{r_col}20; padding:6px; border-radius:4px;">
<div style="color:{r_col}; font-size:10px; font-weight:800; font-family:monospace; background:rgba(0,0,0,0.75); display:inline-block; padding:1px 5px; border-radius:2px;">
AI DETECT: {cam['ai_status']}
</div>
</div>
</div>
<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:10px; padding-top:8px; border-top:1px solid #F1F5F9; font-size:11px;">
<div><span style="color:#64748B;">Water Depth:</span> <b style="color:#0F172A;">{cam['water_depth_cm']} cm</b></div>
<div><span style="color:#64748B;">Blockage Index:</span> <b style="color:{r_col};">{cam['blockage_index']}%</b></div>
<div><span style="color:#64748B;">Incidents Today:</span> <b style="color:#0F172A;">{cam['incidents_today']}</b></div>
<div><span style="color:#64748B;">Optical Status:</span> <b style="color:#16A34A;">Optimal</b></div>
</div>
</div>
""").strip()
                st.html(card_html)

    with tab_upload:
        st.markdown("### 🚀 Real-Time CCTV Surveillance & AI Detection Pipeline")
        st.markdown(
            "Upload CCTV footage or select a municipal optical feed. "
            "Gemini finds drainage, garbage and road problems and anyone dumping waste; a local YOLOE model "
            "outlines and tracks every object frame by frame and sorts garbage by waste stream."
        )

        sample_ganga_path = settings.UPLOADS_DIR / "ganga.mp4"
        has_sample = sample_ganga_path.exists()

        col_src1, col_src2 = st.columns([1.5, 1])
        with col_src1:
            uploaded_file = st.file_uploader("Upload CCTV Video Clip (.mp4, .mov, .webm)", type=["mp4", "mov", "webm"])
            if has_sample:
                use_sample = st.checkbox("⚡ Use Municipal CCTV Sample Feed (Ganga Dham Conduit, 1080p)", value=True if not uploaded_file else False)
            else:
                use_sample = False

            cam_choice = st.selectbox("Assign Camera Stream", [c["name"] + f" ({c['id']})" for c in CCTV_CAMERAS[:3]])
            custom_gps = st.text_input("Camera GPS Coordinates", value="18.4850, 73.8650")

        with col_src2:
            st.markdown("#### What runs on the video")
            st.markdown(
                """
                - **Gemini (Pass A):** drains, manholes, garbage, potholes and other road hazards
                - **Gemini (Pass C):** water level and blockage at each drain it finds
                - **Local YOLOE:** per-object masks + tracking, waste-stream sorting
                - **Gemini (Pass B):** people dumping garbage, vehicle and number plate
                """
            )
            run_violator_pass = st.checkbox("Pass B: Detect Illegal Waste Dumping Violators", value=True)

        execute_clicked = st.button("⚡ Execute Real-Time Surveillance & Detection", type="primary", use_container_width=True)

        if execute_clicked:
            target_video_path = None
            if uploaded_file:
                clean_name = uploaded_file.name.replace("\\", "").replace(" ", "_")
                save_path = settings.UPLOADS_DIR / clean_name
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                target_video_path = save_path
            elif use_sample and has_sample:
                target_video_path = sample_ganga_path

            if target_video_path:
                with st.status("Processing Real-Time Surveillance Video...", expanded=True) as status:
                    status.write(f"📁 Source video clip: `{target_video_path.name}` ({target_video_path.stat().st_size / (1024*1024):.2f} MB)")
                    try:
                        pipeline = CivicEyePipeline()
                        result = pipeline.process_video(
                            video_path=target_video_path,
                            source_gps=custom_gps,
                            run_pass_b=run_violator_pass,
                            progress_cb=lambda msg: status.write(f"⏳ {msg}"),
                        )
                        status.update(label="✅ Real-Time Video Surveillance Analysis Complete!", state="complete", expanded=False)
                        st.success(f"Surveillance analysis complete! Real-time detection stream compiled for Job `{result['job_id'][:8]}`.")
                        st.session_state["active_job_id"] = result["job_id"]
                    except Exception as e:
                        status.update(label="❌ Analysis Failed", state="error")
                        st.error(f"Error during video surveillance processing: {e}")
            else:
                st.warning("Please upload a video file or check the sample feed option.")

        render_job_results()


def _load_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    path = settings.EVIDENCE_DIR / job_id / "result.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _score_metric(col, label: str, score, band: str) -> None:
    if score is None:
        col.metric(label, "Not assessed")
    else:
        col.metric(label, f"{score:.0f} / 100", band, delta_color="off")


def render_job_results():
    """Show the real outputs of an analysed video: evidence video, objects, waste streams, scores."""
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.status == "completed").order_by(Job.created_at.desc()).limit(20).all()
        jobs = [j for j in jobs if _load_job_result(j.id)]
        if not jobs:
            st.info("Upload a video and run the analysis to see detections here.")
            return

        st.markdown("---")
        active = st.session_state.get("active_job_id")
        ids = [j.id for j in jobs]
        idx = ids.index(active) if active in ids else 0
        job = st.selectbox(
            "Analysed video",
            jobs,
            index=idx,
            format_func=lambda j: f"{j.filename} · {j.created_at:%d %b %H:%M} · job {j.id[:8]}",
        )
        result = _load_job_result(job.id)
        objects = result.get("objects")

        video_path = Path(result["annotated_video_path"])
        if video_path.is_file():
            st.video(str(video_path))
        st.caption(
            "Coloured outlines are per-object segmentation masks from the local detector, each with a track ID "
            "that follows the object across frames. White boxes marked VLM are Gemini's findings, shown around "
            "the frame Gemini picked."
        )

        # Scores (deterministic, from observed evidence only)
        c1, c2, c3, c4 = st.columns(4)
        _score_metric(c1, "Drainage risk", result.get("drainage_score"), result.get("drainage_band", ""))
        _score_metric(c2, "Garbage risk", result.get("garbage_score"), result.get("garbage_band", ""))
        _score_metric(c3, "Composite risk", result.get("composite_score"), result.get("composite_band", ""))
        c4.metric("Dumping violations", result.get("violations_count", 0), "sent to officer review", delta_color="off")
        sources = result.get("score_sources") or {}
        if sources:
            st.caption("Score inputs: " + " · ".join(f"{k.replace('_', ' ')}: {v}" for k, v in sources.items()))
        if result.get("drainage_score") is None:
            st.caption("Drainage is only scored when Gemini finds a drain or manhole and assesses it (Pass C).")

        # Object segregation
        st.markdown("#### 🧩 Objects detected and tracked")
        if objects is None:
            st.warning("The local detector did not run for this video, so only Gemini's findings are available.")
        elif not objects["objects"]:
            st.info(f"No objects were tracked across {objects['frames_analyzed']} analysed frames.")
        else:
            rows = [
                {
                    "Track": f"#{o['track_id']}",
                    "Object": o["label"],
                    "Group": CATEGORY_LABELS.get(o["category"], o["category"]),
                    "Waste stream": WASTE_TYPE_LABELS.get(o["waste_type"], "") if o["waste_type"] else "",
                    "Seen (s)": f"{o['first_sec']:.1f}–{o['last_sec']:.1f}",
                    "Frames": o["frames_seen"],
                    "Max confidence": round(o["max_confidence"], 2),
                }
                for o in objects["objects"]
            ]
            st.dataframe(rows, hide_index=True, use_container_width=True)
            st.caption(
                f"{objects['detector']} · {objects['frames_analyzed']} frames analysed · "
                f"objects seen in fewer than 2 analysed frames are ignored as flicker."
            )

            w_col, t_col = st.columns([1, 1.4])
            with w_col:
                st.markdown("**♻️ Garbage by waste stream**")
                waste = objects.get("waste_breakdown") or {}
                if waste:
                    st.bar_chart({WASTE_TYPE_LABELS[k]: v for k, v in waste.items()}, horizontal=True)
                else:
                    st.caption("No garbage objects tracked.")
            with t_col:
                st.markdown("**📈 Objects in view over time**")
                timeline = objects.get("timeline") or []
                if timeline:
                    cats = sorted({k for row in timeline for k in row if k != "sec"})
                    chart = {CATEGORY_LABELS.get(c, c): [row.get(c, 0) for row in timeline] for c in cats}
                    st.line_chart(chart)
                    st.caption("x-axis: seconds into the video")

        # Gemini findings
        incidents = (
            db.query(Incident)
            .filter(Incident.job_id == job.id, Incident.subtype != "dumping_violation")
            .order_by(Incident.severity.desc())
            .all()
        )
        st.markdown("#### 🔍 Gemini findings")
        if not incidents:
            st.info("Gemini reported no drainage, garbage or road issues in this video.")
        for inc in incidents:
            with st.container(border=True):
                img_col, txt_col = st.columns([1, 2])
                frame = next((e.path for e in inc.evidences if e.kind == "annotated" and Path(e.path).is_file()), None)
                if frame:
                    img_col.image(frame, use_container_width=True)
                sent = {log.channel: log.status for log in inc.alerts}
                txt_col.markdown(
                    f"**{inc.subtype.replace('_', ' ').title()}** ({inc.type}) · severity {inc.severity}/5 · "
                    f"at {inc.video_ts} · confidence {inc.confidence:.0%}"
                )
                txt_col.write(inc.description)
                if inc.sewer_score:
                    txt_col.caption(f"Sewer overflow score: {inc.sewer_score.score:.0f}/100 ({inc.sewer_score.band})")
                if sent:
                    txt_col.caption("Alerts: " + ", ".join(f"{c} {s}" for c, s in sent.items()))
                elif inc.severity >= settings.ALERT_MIN_SEVERITY:
                    txt_col.caption("Alert not sent: no alert channel configured.")
    finally:
        db.close()
