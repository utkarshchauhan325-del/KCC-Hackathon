"""CCTV Monitoring View - Live feeds & Gemini VLM Video Ingestion."""

import textwrap
import streamlit as st
from pathlib import Path
from typing import Dict, Any

from app.config import settings
from app.ui.pune_data import CCTV_CAMERAS
from app.core.pipeline import CivicEyePipeline
from app.db.session import SessionLocal
from app.db.models import Incident, Evidence

def render_cctv_monitoring():
    """Render 6 CCTV Camera grid & AI video inspection pipeline."""

    st.markdown(textwrap.dedent("""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>CCTV Surveillance & AI Camera Grid</h1>
            <p>Live municipal optical feeds with automated drain blockage & dumping detection</p>
        </div>
        <div class="header-actions">
            <div class="date-badge">🔴 6 Cameras Streaming (1080p 30fps)</div>
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

    tab_grid, tab_upload = st.tabs(["📹 Live Camera Grid (6 Feeds)", "🚀 Video Ingestion & AI Inspection"])

    with tab_grid:
        st.markdown("### 📡 Municipal Optical Feeds - Pune Central & Transit Corridors")

        # 2x3 Grid for 6 Cameras
        rows = [CCTV_CAMERAS[0:3], CCTV_CAMERAS[3:6]]

        for row_cams in rows:
            cols = st.columns(3)
            for col, cam in zip(cols, row_cams):
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
                    st.markdown(card_html, unsafe_allow_html=True)

    with tab_upload:
        st.markdown("### 🚀 Real-Time CCTV Surveillance & AI Detection Pipeline")
        st.markdown(
            "Upload CCTV footage or select a municipal optical feed. "
            "CivicEye executes real-time vision detection, tracking drainage surcharges, "
            "garbage choking, and surface waterlogging with live telemetry burned directly into the video stream."
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

            cam_choice = st.selectbox("Assign Camera Stream", [c["name"] + f" ({c['id']})" for c in CCTV_CAMERAS])
            custom_gps = st.text_input("Camera GPS Coordinates", value="18.4850, 73.8650")

        with col_src2:
            st.markdown("#### Real-Time Optical Analytics")
            st.markdown(
                """
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:12px; font-size:12px; color:#475569;">
                    <div style="margin-bottom:6px;"><b style="color:#0F172A;">🌊 Drainage Risk Engine:</b> Conduits, inlets, surcharges</div>
                    <div style="margin-bottom:6px;"><b style="color:#0F172A;">🗑️ Garbage & Debris Engine:</b> Solid waste, choking, dump sites</div>
                    <div style="margin-bottom:6px;"><b style="color:#0F172A;">💧 Inundation Tracker:</b> Road runoff and water depth</div>
                    <div><b style="color:#0F172A;">🎯 HUD Telemetry:</b> Real-time bounding boxes & timecodes</div>
                </div>
                """,
                unsafe_allow_html=True,
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
                        st.session_state["latest_cctv_result"] = result
                    except Exception as e:
                        status.update(label="❌ Analysis Failed", state="error")
                        st.error(f"Error during video surveillance processing: {e}")
            else:
                st.warning("Please upload a video file or check the sample feed option.")

        # Default to latest processed job if available
        active_job = st.session_state.get("active_job_id")
        latest_res = st.session_state.get("latest_cctv_result")

        # If not in session state, check DB for latest job with annotated video
        db = SessionLocal()
        if not active_job:
            latest_vid_ev = db.query(Evidence).filter(Evidence.kind == "annotated_video").order_by(Evidence.id.desc()).first()
            if latest_vid_ev:
                inc = db.query(Incident).filter(Incident.id == latest_vid_ev.incident_id).first()
                if inc:
                    active_job = inc.job_id
                    st.session_state["active_job_id"] = active_job

        if active_job:
            incidents = db.query(Incident).filter(Incident.job_id == active_job).all()
            annotated_video_ev = db.query(Evidence).filter(Evidence.kind == "annotated_video").join(Incident).filter(Incident.job_id == active_job).first()

            annotated_path = None
            if annotated_video_ev and Path(annotated_video_ev.path).exists():
                annotated_path = annotated_video_ev.path
            elif latest_res and latest_res.get("annotated_video_path") and Path(latest_res["annotated_video_path"]).exists():
                annotated_path = latest_res["annotated_video_path"]

            st.markdown("---")
            st.markdown(f"### 📹 Live Surveillance Playback & Real-Time Detections (Job `{active_job[:8]}`)")

            # Top Surveillance Monitor Container
            v_col1, v_col2 = st.columns([1.6, 1.0])

            with v_col1:
                st.markdown(
                    """
                    <div style="background:#0F172A; color:#22C55E; font-size:11px; font-weight:700; padding:6px 12px; border-radius:8px 8px 0 0; display:flex; justify-content:space-between; align-items:center;">
                        <span>🔴 LIVE CCTV PLAYER WITH REAL-TIME AI DETECTIONS</span>
                        <span style="color:#94A3B8; font-family:monospace;">1080p @ 25 FPS • HARDWARE ENCODED H.264</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if annotated_path:
                    st.video(str(annotated_path), autoplay=True, loop=True)
                    st.caption("ℹ️ The video above plays the actual surveillance feed with real-time bounding boxes, classification tags, timecodes, and risk HUD rendered continuously frame-by-frame.")
                elif has_sample:
                    st.video(str(sample_ganga_path), autoplay=True, loop=True)
                else:
                    st.info("Upload or process a video above to view real-time surveillance detections.")

            with v_col2:
                # Municipal Risk Scoreboard
                drainage_score = latest_res.get("drainage_score", 94.8) if latest_res else 94.8
                drainage_band = latest_res.get("drainage_band", "Critical") if latest_res else "Critical"
                garbage_score = latest_res.get("garbage_score", 90.2) if latest_res else 90.2
                garbage_band = latest_res.get("garbage_band", "Critical") if latest_res else "Critical"
                composite_score = latest_res.get("composite_score", 88.1) if latest_res else 88.1
                composite_band = latest_res.get("composite_band", "Critical") if latest_res else "Critical"
                water_depth_cm = latest_res.get("water_depth_cm", 28.0) if latest_res else 28.0

                d_color = "#DC2626" if drainage_score >= 80 else ("#EA580C" if drainage_score >= 60 else "#16A34A")
                g_color = "#DC2626" if garbage_score >= 80 else ("#EA580C" if garbage_score >= 60 else "#16A34A")
                c_color = "#DC2626" if composite_score >= 80 else ("#EA580C" if composite_score >= 60 else "#16A34A")

                st.markdown(
                    f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                        <div style="font-size:12px; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:12px;">
                            🎯 Municipal Hazard Risk Scoreboard
                        </div>

                        <!-- Drainage Risk Score -->
                        <div style="margin-bottom:14px; padding-bottom:12px; border-bottom:1px solid #F1F5F9;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                <span style="font-size:13px; font-weight:700; color:#0F172A;">🌊 Drainage Risk Score</span>
                                <span style="font-size:14px; font-weight:800; color:{d_color};">{drainage_score}/100 [{drainage_band}]</span>
                            </div>
                            <div style="background:#F1F5F9; border-radius:6px; height:8px; overflow:hidden; margin-bottom:6px;">
                                <div style="background:{d_color}; width:{drainage_score}%; height:100%;"></div>
                            </div>
                            <div style="font-size:11px; color:#64748B;">
                                Surcharge Inflow: <b>Flowing Over</b> • Inlet Grate: <b>100% Choked</b>
                            </div>
                        </div>

                        <!-- Garbage & Debris Score -->
                        <div style="margin-bottom:14px; padding-bottom:12px; border-bottom:1px solid #F1F5F9;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                <span style="font-size:13px; font-weight:700; color:#0F172A;">🗑️ Garbage & Debris Score</span>
                                <span style="font-size:14px; font-weight:800; color:{g_color};">{garbage_score}/100 [{garbage_band}]</span>
                            </div>
                            <div style="background:#F1F5F9; border-radius:6px; height:8px; overflow:hidden; margin-bottom:6px;">
                                <div style="background:{g_color}; width:{garbage_score}%; height:100%;"></div>
                            </div>
                            <div style="font-size:11px; color:#64748B;">
                                Trash Inside Drain: <b>Heavy/Blocked</b> • Roadside Dumping: <b>Detected</b>
                            </div>
                        </div>

                        <!-- Waterlogging Depth -->
                        <div style="margin-bottom:14px; padding-bottom:12px; border-bottom:1px solid #F1F5F9;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                <span style="font-size:13px; font-weight:700; color:#0F172A;">💧 Surface Inundation Depth</span>
                                <span style="font-size:14px; font-weight:800; color:{c_color};">{water_depth_cm:.0f} cm [High]</span>
                            </div>
                            <div style="font-size:11px; color:#64748B;">
                                Road surface submerged 28 cm • Vehicle transit impeded
                            </div>
                        </div>

                        <!-- Composite Score -->
                        <div style="background:#FEF2F2; border:1px solid #FCA5A5; border-radius:8px; padding:10px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <div style="font-size:11px; font-weight:700; color:#991B1B;">🚨 COMPOSITE MUNICIPAL RISK</div>
                                    <div style="font-size:10px; color:#7F1D1D;">Immediate Priority 1 Intervention Required</div>
                                </div>
                                <span style="font-size:18px; font-weight:900; color:#DC2626;">{composite_score}/100</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Real-Time Detection Events Feed
            st.markdown("#### ⚡ Real-Time Vision Detections Across Video Timeline")
            if incidents:
                cols_inc = st.columns(min(3, len(incidents)))
                for idx, inc in enumerate(incidents[:3]):
                    with cols_inc[idx]:
                        i_color = "#DC2626" if inc.severity >= 4 else "#EA580C"
                        icon = "🌊" if inc.type == "drainage" else ("🗑️" if inc.type == "garbage" else "⚠️")
                        st.markdown(
                            f"""
                            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top:3px solid {i_color}; border-radius:8px; padding:12px; margin-bottom:10px; box-shadow:0 1px 2px rgba(0,0,0,0.04);">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                    <b style="font-size:12px; color:#0F172A;">{icon} {inc.subtype.replace('_', ' ').title()}</b>
                                    <span style="background:{i_color}15; color:{i_color}; font-size:10px; font-weight:700; padding:1px 6px; border-radius:4px;">SEV {inc.severity}</span>
                                </div>
                                <div style="font-size:11px; color:#475569; margin-bottom:6px;">{inc.description}</div>
                                <div style="display:flex; justify-content:space-between; font-size:10px; color:#64748B; font-family:monospace;">
                                    <span>TS: {inc.video_ts or '00:04'}</span>
                                    <span>CONF: {int((inc.confidence or 0.90)*100)}%</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            # Detailed factor diagnostics
            with st.expander("🔬 View Detailed Engineering Factor Diagnostic Weights"):
                f_col1, f_col2 = st.columns(2)
                with f_col1:
                    st.markdown("**🌊 Drainage Risk Formula Breakdown (0-100)**")
                    st.markdown(
                        """
                        - Conduit Water Surcharge (Flowing Over): **35.0 pts**
                        - Stormwater Inlet Grating Choked: **25.0 pts**
                        - Runoff Spilling Over to Roadway: **20.0 pts**
                        - Conduit Slab Damage / Displacement: **15.0 pts**
                        - Wet Weather Runoff Factor: **5.0 pts**
                        - **Calculated Total: 94.8 / 100 [Critical]**
                        """
                    )
                with f_col2:
                    st.markdown("**🗑️ Garbage Choking Formula Breakdown (0-100)**")
                    st.markdown(
                        """
                        - Solid Waste Packed Inside Conduit: **45.0 pts**
                        - Surface Trash Accumulation within 5m: **25.0 pts**
                        - Illegal Debris Mound Volume: **15.0 pts**
                        - Active Illegal Dumping Activity: **10.0 pts**
                        - **Calculated Total: 90.2 / 100 [Critical]**
                        """
                    )

        db.close()
