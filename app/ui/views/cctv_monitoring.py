"""CCTV Monitoring View - Live feeds & Gemini VLM Video Ingestion."""

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

    st.markdown("""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>CCTV Surveillance & AI Camera Grid</h1>
            <p>Live municipal optical feeds with automated drain blockage & dumping detection</p>
        </div>
        <div class="header-actions">
            <div class="date-badge">🔴 6 Cameras Streaming (1080p 30fps)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_grid, tab_upload = st.tabs(["📹 Live Camera Grid (6 Feeds)", "🚀 Video Ingestion & AI Inspection"])

    with tab_grid:
        st.markdown("### 📡 Municipal Optical Feeds - Pune Central & Transit Corridors")

        # 2x3 Grid for 6 Cameras
        rows = [CCTV_CAMERAS[0:3], CCTV_CAMERAS[3:6]]

        for row_cams in rows:
            cols = st.columns(3)
            for col, cam in zip(cols, row_cams):
                with col:
                    # Risk color pill
                    r_col = "#DC2626" if cam["risk_level"] == "Critical" else ("#EA580C" if cam["risk_level"] == "High" else "#16A34A")

                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:12px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <div>
                                <b style="font-size:13px; color:#0F172A;">{cam['name']}</b>
                                <div style="font-size:11px; color:#64748B;">{cam['id']} • Zone {cam['zone']}</div>
                            </div>
                            <span style="background:{r_col}15; color:{r_col}; font-weight:700; font-size:10px; padding:2px 8px; border-radius:10px; border:1px solid {r_col}40;">
                                {cam['risk_level'].upper()}
                            </span>
                        </div>

                        <!-- Simulated Camera View with AI Bounding Box Overlays -->
                        <div style="position:relative; width:100%; height:180px; background:#0F172A; border-radius:8px; overflow:hidden; display:flex; align-items:center; justify-content:center;">
                            <!-- Dark street scene simulation background -->
                            <div style="position:absolute; inset:0; opacity:0.35; background: radial-gradient(circle at 50% 50%, #334155 0%, #020617 100%);"></div>

                            <!-- Live watermark -->
                            <div style="position:absolute; top:8px; left:8px; background:rgba(0,0,0,0.6); color:#22C55E; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px; font-family:monospace;">
                                REC ● {cam['stream_fps']} FPS
                            </div>

                            <div style="position:absolute; top:8px; right:8px; background:rgba(0,0,0,0.6); color:#F8FAFC; font-size:10px; padding:2px 6px; border-radius:4px; font-family:monospace;">
                                {cam['lat']}, {cam['lng']}
                            </div>

                            <!-- AI Detection Bounding Box -->
                            <div style="position:absolute; bottom:20px; left:20px; right:20px; border:2px dashed {r_col}; background:{r_col}15; padding:6px; border-radius:4px;">
                                <div style="color:{r_col}; font-size:10px; font-weight:800; font-family:monospace; background:rgba(0,0,0,0.7); display:inline-block; padding:1px 4px; border-radius:2px;">
                                    AI DETECT: {cam['ai_status']}
                                </div>
                            </div>
                        </div>

                        <!-- Telemetry meters below camera -->
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:10px; padding-top:8px; border-top:1px solid #F1F5F9; font-size:11px;">
                            <div>
                                <span style="color:#64748B;">Water Depth:</span>
                                <b style="color:#0F172A; margin-left:4px;">{cam['water_depth_cm']} cm</b>
                            </div>
                            <div>
                                <span style="color:#64748B;">Blockage Index:</span>
                                <b style="color:{r_col}; margin-left:4px;">{cam['blockage_index']}%</b>
                            </div>
                            <div>
                                <span style="color:#64748B;">Incidents Today:</span>
                                <b style="color:#0F172A; margin-left:4px;">{cam['incidents_today']}</b>
                            </div>
                            <div>
                                <span style="color:#64748B;">Optical Status:</span>
                                <b style="color:#16A34A; margin-left:4px;">Optimal</b>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    with tab_upload:
        st.markdown("### 🚀 Video Ingestion & Vision-Language Model Inspection")
        st.write("Upload raw CCTV or drone footage (.mp4, .mov) to run Gemini VLM Passes (A: Civic Hazards, B: Violator Detection, C: Sewer Overflow Risk Scoring).")

        u_col1, u_col2 = st.columns([1.5, 1])
        with u_col1:
            uploaded_file = st.file_uploader("Upload CCTV Video Clip", type=["mp4", "mov", "webm"])
            cam_choice = st.selectbox("Assign Camera Stream", [c["name"] + f" ({c['id']})" for c in CCTV_CAMERAS])
            custom_gps = st.text_input("Camera GPS Coordinates", value="18.5255, 73.8415")

        with u_col2:
            st.markdown("#### Inspection Passes")
            pass_c = st.checkbox("Pass C: Deterministic Sewer Overflow Scoring (0-100)", value=True)
            pass_b = st.checkbox("Pass B: Violator Detection & Plate OCR", value=False)
            blur_bystanders = st.checkbox("Enforce DPDP Bystander Privacy Blurring", value=True)

        if uploaded_file and st.button("⚡ Execute AI Inspection Pipeline", type="primary", use_container_width=True):
            clean_name = uploaded_file.name.replace("\\", "").replace(" ", "_")
            save_path = settings.UPLOADS_DIR / clean_name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.status("Analyzing footage with Gemini VLM...", expanded=True) as status:
                status.write(f"📁 Video saved to municipal staging: `{save_path.name}` ({save_path.stat().st_size / (1024*1024):.2f} MB)")
                try:
                    pipeline = CivicEyePipeline()
                    result = pipeline.process_video(
                        video_path=save_path,
                        source_gps=custom_gps,
                        run_pass_b=pass_b,
                        progress_cb=lambda msg: status.write(f"⏳ {msg}")
                    )
                    status.update(label="✅ Analysis Complete!", state="complete", expanded=False)
                    st.success(f"Inspection complete! Generated {result.get('incidents_count', 0)} incident records in database.")
                    st.session_state["active_job_id"] = result["job_id"]
                except Exception as e:
                    status.update(label="❌ Inspection Failed", state="error")
                    st.error(f"Error during video inspection: {e}")

        # If a job was recently processed, display the evidence
        active_job = st.session_state.get("active_job_id")
        if active_job:
            db = SessionLocal()
            incidents = db.query(Incident).filter(Incident.job_id == active_job).all()
            if incidents:
                st.markdown("---")
                st.subheader(f"✨ AI Findings for Job `{active_job[:8]}` ({len(incidents)} Incidents)")
                for inc in incidents:
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        st.markdown(f"**{inc.subtype.title()}** (Severity {inc.severity})")
                        st.write(inc.description)
                        if inc.sewer_score:
                            st.info(f"🌊 Sewer Overflow Risk Score: {inc.sewer_score.score}/100 ({inc.sewer_score.band})")
                    with c2:
                        evidences = db.query(Evidence).filter(Evidence.incident_id == inc.id).all()
                        annotated = next((e for e in evidences if e.kind == "annotated"), None)
                        if annotated and Path(annotated.path).exists():
                            st.image(str(annotated.path), caption="Annotated Evidence Frame", use_container_width=True)
            db.close()
