"""CCTV view: camera list and video analysis (Gemini findings + local detector)."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import plotly.graph_objects as go
import streamlit as st

from app.config import settings
from app.ui.pune_data import CCTV_CAMERAS, PUNE_LOCATIONS
from app.core.pipeline import CivicEyePipeline
from app.db.session import SessionLocal
from app.db.models import Incident, Job
from app.core.detector import CATEGORY_LABELS, WASTE_TYPE_LABELS
from app.ui.components.charts import _style
from app.ui.components.styles import ACCENT, chip, icon, page_header, section_title, status_pill

_CHART_CONFIG = {"displayModeBar": False}

# Distinctive solid waste stream palette
WASTE_STREAM_COLORS = {
    "dry_plastic": "#0284C7",    # Vivid Ocean Blue
    "dry_paper": "#6366F1",      # Indigo
    "wet_organic": "#10B981",    # Emerald
    "construction": "#F59E0B",   # Warm Amber
    "e_waste": "#8B5CF6",        # Violet Purple
    "mixed": "#64748B",          # Slate
}

# Detection telemetry line styling
DETECTION_PALETTE = {
    "person": {"color": "#10B981", "fill": "rgba(16, 185, 129, 0.08)"},    # Emerald
    "vehicle": {"color": "#0284C7", "fill": "rgba(2, 132, 199, 0.08)"},    # Ocean Blue
    "drainage": {"color": "#3B82F6", "fill": "rgba(59, 130, 246, 0.08)"},   # Royal Blue
    "road": {"color": "#F59E0B", "fill": "rgba(245, 158, 11, 0.08)"},       # Amber
    "bin": {"color": "#8B5CF6", "fill": "rgba(139, 92, 246, 0.08)"},        # Purple
    "plate": {"color": "#EC4899", "fill": "rgba(236, 72, 153, 0.08)"},      # Pink
}


def _get_all_pune_areas() -> List[Dict[str, Any]]:
    """Build a comprehensive list of all Pune Municipal Corporation locations and cameras."""
    areas: List[Dict[str, Any]] = []
    seen = set()

    # 1. Monitored locations across Pune (53 wards & critical junctions)
    for loc in PUNE_LOCATIONS:
        if loc["name"] not in seen:
            seen.add(loc["name"])
            areas.append({
                "id": loc.get("id", "LOC"),
                "name": loc["name"],
                "ward": loc.get("ward", "Pune Central"),
                "zone": loc.get("zone", "Central"),
                "lat": float(loc["lat"]),
                "lng": float(loc["lng"]),
                "drain_type": loc.get("drain_type", "Culvert / Drain"),
                "risk_level": loc.get("risk_level", "Medium"),
                "source": "Monitored Junction",
            })

    # 2. Fixed CCTV surveillance cameras
    for cam in CCTV_CAMERAS:
        if cam["name"] not in seen:
            seen.add(cam["name"])
            areas.append({
                "id": cam.get("id", "CAM"),
                "name": cam["name"],
                "ward": f"{cam.get('zone', 'Central')} Corridor",
                "zone": cam.get("zone", "Central"),
                "lat": float(cam["lat"]),
                "lng": float(cam["lng"]),
                "drain_type": cam.get("ai_status", "Fixed CCTV Feed"),
                "risk_level": cam.get("risk_level", "Medium"),
                "source": "CCTV Camera Feed",
            })

    return sorted(areas, key=lambda a: (a["zone"], a["name"]))


def render_cctv_monitoring():
    """Render the camera list and the video analysis workflow."""

    st.markdown(page_header(
        "CCTV analysis",
        "Run recorded camera footage through drain, garbage and dumping detection. Findings go to the priority queue.",
        eyebrow="Cameras",
        meta=[f"<b>{len(CCTV_CAMERAS[:3])}</b> cameras active", f"<b>{len(PUNE_LOCATIONS)}</b> monitored wards", "Video upload and review"],
    ), unsafe_allow_html=True)

    tab_upload, tab_grid = st.tabs(["Analyse video", "Cameras"])

    with tab_grid:
        st.markdown(section_title("Assigned cameras", "Central and transit corridors. Figures are from the most recent analysis of each camera."), unsafe_allow_html=True)
        cols = st.columns(3)
        for col, cam in zip(cols, CCTV_CAMERAS[:3]):
            with col:
                st.markdown(
                    f'<div class="fg-card" style="padding:14px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:10px;">'
                    f'<div style="min-width:0;"><div style="font-size:13.5px;font-weight:600;color:#0B1220;">{cam["name"]}</div>'
                    f'<div class="fg-mono" style="font-size:11px;color:#64708A;">{cam["id"]} &middot; {cam["zone"]}</div></div>'
                    f'{status_pill(cam["risk_level"])}</div>'
                    f'<div style="height:150px;border-radius:10px;background:linear-gradient(180deg,#F1F4F8,#E8EDF3);border:1px solid #E3E8EF;'
                    f'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;color:#94A0B4;">'
                    f'{icon("camera", 22)}<span style="font-size:11.5px;">No stream connected</span>'
                    f'<span class="fg-mono" style="font-size:10.5px;">{cam["lat"]}, {cam["lng"]}</span></div>'
                    f'<div class="fg-kv" style="margin-top:12px;border-top:none;padding-top:0;">'
                    f'<div><span class="fg-k">Water depth</span><span class="fg-v mono">{cam["water_depth_cm"]} cm</span></div>'
                    f'<div><span class="fg-k">Blockage</span><span class="fg-v mono">{cam["blockage_index"]}%</span></div>'
                    f'<div><span class="fg-k">Incidents today</span><span class="fg-v mono">{cam["incidents_today"]}</span></div>'
                    f'<div><span class="fg-k">Last finding</span><span class="fg-v" style="font-size:12px;">{cam["ai_status"]}</span></div>'
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

    with tab_upload:
        st.markdown(section_title(
            "Analyse surveillance footage",
            "Upload CCTV footage or select pre-loaded municipal feeds. Gemini pinpoints drain overflows, waste heaps, and dumping violators, while local YOLOE segments and tracks objects frame by frame.",
        ), unsafe_allow_html=True)

        all_areas = _get_all_pune_areas()
        zones = ["All Zones", "Central", "West", "East", "South", "North"]

        # Pre-loaded sample files in data/uploads
        sample_options = {
            "None (Upload custom footage)": None,
            "Ganga Dham Conduit (Drain blockage & trash)": settings.UPLOADS_DIR / "ganga.mp4",
            "Chinchwad Road (Illegal dumping & vehicles)": settings.UPLOADS_DIR / "chinchuuuuuuuuu.mp4",
            "Plastic Fischer Conduit (River nala debris)": settings.UPLOADS_DIR / "Cleaning_tributaries_to_Ganga_River_in_Varanasi_-_Plastic_Fischer_(1080p).mp4",
        }

        # ------------------------------------------------------------------
        # Two-Column Layout: Left = Video Details, Right = Video Preview/Upload
        # ------------------------------------------------------------------
        col_details, col_video = st.columns([1.1, 1.3], gap="large")

        # --- RIGHT COLUMN: Drag & Drop Uploader and Video Player ---
        with col_video:
            st.markdown('<div class="fg-card-title" style="margin-bottom:8px;">Surveillance footage feed</div>', unsafe_allow_html=True)

            uploaded_file = st.file_uploader(
                "Upload video footage (.mp4, .mov, .webm)",
                type=["mp4", "mov", "webm"],
                help="Drag and drop or select video file from CCTV camera archive.",
            )

            sample_choice = st.selectbox(
                "Or choose pre-loaded municipal CCTV footage",
                list(sample_options.keys()),
                index=0 if uploaded_file else 1,
            )

            # Determine the active video source
            target_video_path: Optional[Path] = None
            active_video_name = ""
            active_video_size_mb = 0.0

            if uploaded_file:
                clean_name = uploaded_file.name.replace("\\", "").replace(" ", "_")
                target_video_path = settings.UPLOADS_DIR / clean_name
                # Save uploaded file
                with open(target_video_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                active_video_name = uploaded_file.name
                active_video_size_mb = uploaded_file.size / (1024 * 1024)
            elif sample_choice != "None (Upload custom footage)":
                cand_path = sample_options[sample_choice]
                if cand_path and cand_path.is_file():
                    target_video_path = cand_path
                    active_video_name = cand_path.name
                    active_video_size_mb = cand_path.stat().st_size / (1024 * 1024)

            # Live Video Player on the Right
            if target_video_path and target_video_path.is_file():
                st.markdown(
                    f'<div style="background:#0F172A; border-radius:12px 12px 0 0; padding:10px 14px; '
                    f'display:flex; justify-content:space-between; align-items:center; color:#F8FAFC; border:1px solid #1E293B; border-bottom:none; margin-top:12px;">'
                    f'<div style="display:flex; align-items:center; gap:8px;">'
                    f'<span style="width:8px; height:8px; border-radius:50%; background:#10B981; display:inline-block;"></span>'
                    f'<span style="font-family:JetBrains Mono, monospace; font-size:12px; font-weight:600;">{active_video_name}</span>'
                    f'</div>'
                    f'<span style="font-family:JetBrains Mono, monospace; font-size:11px; color:#94A3B8;">{active_video_size_mb:.2f} MB</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.video(str(target_video_path))
                st.caption(f"Footage ready for AI inspection &middot; {active_video_name} ({active_video_size_mb:.2f} MB)")
            else:
                st.markdown(
                    f'<div style="height:310px; border-radius:12px; background:linear-gradient(180deg,#F8FAFC,#EEF2F6); '
                    f'border:2px dashed #CBD5E1; display:flex; flex-direction:column; align-items:center; justify-content:center; '
                    f'gap:10px; color:#64748B; margin-top:12px;">'
                    f'{icon("camera", 36, "#94A3B8")}'
                    f'<div style="font-weight:600; font-size:14px; color:#334155;">No footage selected</div>'
                    f'<div style="font-size:12px; color:#64748B; max-width:280px; text-align:center;">'
                    f'Drag & drop a video above or choose a pre-loaded municipal CCTV clip.'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

        # --- LEFT COLUMN: Video Details & Metadata ---
        with col_details:
            st.markdown('<div class="fg-card-title" style="margin-bottom:8px;">Camera area & video details</div>', unsafe_allow_html=True)

            # Area Filter & Selector
            z_col, a_col = st.columns([1, 2])
            with z_col:
                selected_zone = st.selectbox("Zone filter", zones, index=0)
            with a_col:
                filtered_areas = all_areas if selected_zone == "All Zones" else [a for a in all_areas if a["zone"] == selected_zone]
                area_names = [f"{a['name']} · {a['ward']} ({a['zone']})" for a in filtered_areas]
                area_idx = st.selectbox("Area / Camera location", range(len(area_names)), format_func=lambda i: area_names[i])
                selected_area = filtered_areas[area_idx]

            # Auto-populated GPS coordinates
            default_gps = f"{selected_area['lat']:.4f}, {selected_area['lng']:.4f}"
            custom_gps = st.text_input("Camera GPS coordinates", value=default_gps)

            # Location Context Card
            st.markdown(
                f'<div class="fg-card" style="padding:12px 14px; margin-bottom:12px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
                f'<span style="font-size:13.5px; font-weight:600; color:#0B1220;">{selected_area["name"]}</span>'
                f'{status_pill(selected_area["risk_level"])}'
                f'</div>'
                f'<div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px;">'
                f'<span class="fg-chip" style="font-size:11px;">{selected_area["ward"]}</span>'
                f'<span class="fg-chip" style="font-size:11px;">{selected_area["zone"]} Zone</span>'
                f'<span class="fg-chip fg-chip-accent" style="font-size:11px;">{selected_area["source"]}</span>'
                f'</div>'
                f'<div style="font-size:11.5px; color:#64708A;">'
                f'Drain structure: <b style="color:#334155;">{selected_area["drain_type"]}</b> &middot; Coordinates: <b class="fg-mono" style="color:#0A7C8F;">{custom_gps}</b>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Video Metadata Card
            if target_video_path and target_video_path.is_file():
                st.markdown(
                    f'<div class="fg-card" style="padding:12px 14px; margin-bottom:12px;">'
                    f'<div style="font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:#64708A; font-weight:600; margin-bottom:6px;">Video Metadata</div>'
                    f'<div style="display:grid; grid-template-columns:1fr 1fr; gap:6px 12px; font-size:12px;">'
                    f'<div><span style="color:#64708A;">File:</span> <span class="fg-mono" style="font-weight:600; color:#0B1220;">{active_video_name}</span></div>'
                    f'<div><span style="color:#64708A;">Size:</span> <span class="fg-mono" style="font-weight:600; color:#0B1220;">{active_video_size_mb:.2f} MB</span></div>'
                    f'<div><span style="color:#64708A;">Format:</span> <span class="fg-mono" style="font-weight:600; color:#0B1220;">{target_video_path.suffix.upper()}</span></div>'
                    f'<div><span style="color:#64708A;">Status:</span> <span style="color:#10B981; font-weight:600;">● Loaded & Ready</span></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

            # Inspection Pipeline Passes
            steps = [
                ("Pass A & C", "Gemini infrastructure scan & sewer overflow depth risk"),
                ("Local YOLOE", "Per-frame segmentation masks & object tracking"),
                ("Pass B", "Illegal dumping violators & vehicle number plate OCR"),
            ]
            pipeline_rows = "".join(
                f'<div style="display:flex;gap:8px;padding:6px 0;border-top:1px solid #EEF1F5;font-size:12px;">'
                f'<span class="fg-mono" style="color:#0A7C8F;font-weight:600;width:80px;">{t}</span>'
                f'<span style="color:#64708A;">{d}</span></div>'
                for t, d in steps
            )
            st.markdown(f'<div class="fg-card" style="padding:12px 14px; margin-bottom:12px;">'
                        f'<div style="font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:#64708A; font-weight:600; margin-bottom:4px;">Pipeline Stages</div>'
                        f'{pipeline_rows}</div>', unsafe_allow_html=True)

            run_violator_pass = st.checkbox("Scan for waste dumping violators (Pass B)", value=True)

            execute_clicked = st.button("⚡ Run Video Analysis", type="primary", use_container_width=True)

            if execute_clicked:
                if target_video_path and target_video_path.is_file():
                    with st.status("Analysing video footage...", expanded=True) as status:
                        status.write(f"Source: `{target_video_path.name}` ({active_video_size_mb:.2f} MB)")
                        try:
                            pipeline = CivicEyePipeline()
                            result = pipeline.process_video(
                                video_path=target_video_path,
                                source_gps=custom_gps,
                                run_pass_b=run_violator_pass,
                                progress_cb=lambda msg: status.write(msg),
                            )
                            status.update(label="Analysis complete", state="complete", expanded=False)
                            st.success(f"Analysis complete for job `{result['job_id'][:8]}`.")
                            st.session_state["active_job_id"] = result["job_id"]
                            st.rerun()
                        except Exception as e:
                            status.update(label="Analysis failed", state="error")
                            st.error(f"Video analysis failed: {e}")
                else:
                    st.warning("Please upload a video file or pick a pre-loaded sample clip.")

        render_job_results()


def _load_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    path = settings.EVIDENCE_DIR / job_id / "result.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _show_evidence_video(path: Path) -> None:
    """Show the evidence video within the right column."""
    if path.is_file():
        st.video(str(path))


def _score_metric(col, label: str, score, band: str) -> None:
    if score is None:
        col.metric(label, "Not assessed")
    else:
        col.metric(label, f"{score:.0f} / 100", band, delta_color="off")


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _stat(label: str, value: str, note: str = "") -> str:
    return (
        f'<div class="fg-kpi" style="padding:12px 14px;"><div class="fg-kpi-label">{label}</div>'
        f'<div class="fg-kpi-row" style="margin-top:6px;"><span class="fg-kpi-value" style="font-size:22px;">{value}</span></div>'
        f'<div style="font-size:11.5px;color:#64708A;margin-top:4px;">{note}</div></div>'
    )


def _waste_shares(waste: Dict[str, float]) -> Dict[str, float]:
    """Return waste-stream shares (0-1)."""
    waste = {k: v for k, v in waste.items() if v is not None}
    total = sum(float(v) for v in waste.values())
    if total <= 0:
        return {}
    if total <= 1.01:
        return {k: float(v) for k, v in waste.items()}
    return {k: float(v) / total for k, v in waste.items()}


def _waste_chart(shares: Dict[str, float]) -> go.Figure:
    """Enhanced horizontal bar chart for solid waste streams with distinct modern colors."""
    items = sorted(shares.items(), key=lambda kv: kv[1])
    labels = [WASTE_TYPE_LABELS.get(k, k) for k, _ in items]
    vals = [v * 100 for _, v in items]
    colors = [WASTE_STREAM_COLORS.get(k, "#0A7C8F") for k, _ in items]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=vals,
        y=labels,
        orientation="h",
        marker=dict(
            color=colors,
            cornerradius=6,
            line=dict(color="rgba(255,255,255,0.7)", width=1.5),
        ),
        text=[f"<b>{v:.1f}%</b>" for v in vals],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(family="JetBrains Mono, monospace", size=11, color="#1E293B"),
        hovertemplate="<b>%{y}</b><br>Share of measured garbage: <b>%{x:.1f}%</b><extra></extra>",
    ))
    _style(fig, max(150, 42 * len(labels) + 36), dict(t=10, b=24, l=10, r=46))
    fig.update_xaxes(
        range=[0, max(vals + [40]) * 1.25 if vals else 100],
        ticksuffix="%",
        showgrid=True,
        gridcolor="#F1F5F9",
        gridwidth=1,
    )
    fig.update_yaxes(
        tickfont=dict(family="Inter, sans-serif", size=12, color="#1E293B"),
        showgrid=False,
    )
    return fig


def _timeline_charts(timeline: List[Dict[str, Any]]) -> Tuple[Optional[go.Figure], Optional[go.Figure]]:
    """Enhanced smooth spline telemetry charts for temporal objects and debris coverage."""
    secs = [row.get("sec", i) for i, row in enumerate(timeline)]
    cats = sorted({k for row in timeline for k in row if k not in ("sec", "garbage_coverage")})

    counts = None
    if cats:
        counts = go.Figure()
        for c in cats:
            style_info = DETECTION_PALETTE.get(c, {"color": "#64748B", "fill": "rgba(100, 116, 139, 0.05)"})
            y_vals = [row.get(c, 0) for row in timeline]
            label = CATEGORY_LABELS.get(c, c.capitalize())
            counts.add_trace(go.Scatter(
                x=secs,
                y=y_vals,
                name=label,
                mode="lines",
                line=dict(color=style_info["color"], width=2.2, shape="spline", smoothing=1.0),
                fill="tozeroy",
                fillcolor=style_info["fill"],
                hovertemplate=f"<b>{label}</b>: %{{y}} in view<extra></extra>",
            ))
        _style(counts, 220, dict(t=24, b=30, l=36, r=14))
        counts.update_layout(
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="right",
                x=1.0,
                font=dict(size=11, color="#475569"),
                bgcolor="rgba(255,255,255,0.7)",
            ),
        )
        counts.update_xaxes(title="Seconds into video", showgrid=True, gridcolor="#F1F5F9", ticksuffix="s")
        counts.update_yaxes(title="Count in frame", rangemode="tozero", showgrid=True, gridcolor="#F1F5F9")

    coverage = None
    if any("garbage_coverage" in row for row in timeline):
        cov_vals = [(row.get("garbage_coverage") or 0) * 100 for row in timeline]
        peak_cov = max(cov_vals) if cov_vals else 0

        coverage = go.Figure()
        coverage.add_trace(go.Scatter(
            x=secs,
            y=cov_vals,
            mode="lines",
            name="Debris Coverage",
            line=dict(color="#EA580C", width=2.4, shape="spline", smoothing=1.1),
            fill="tozeroy",
            fillcolor="rgba(234, 88, 12, 0.12)",
            hovertemplate="Debris coverage: <b>%{y:.1f}%</b> of frame<extra></extra>",
        ))
        if peak_cov >= 8:
            coverage.add_hline(
                y=10.0,
                line_dash="dot",
                line_color="#DC2626",
                line_width=1.2,
                annotation_text="Accumulation Alert (10%)",
                annotation_position="top left",
                annotation_font=dict(size=10, color="#DC2626", family="JetBrains Mono"),
            )
        _style(coverage, 200, dict(t=14, b=30, l=40, r=14))
        coverage.update_layout(hovermode="x")
        coverage.update_xaxes(title="Seconds into video", showgrid=True, gridcolor="#F1F5F9", ticksuffix="s")
        coverage.update_yaxes(title="% of frame area", ticksuffix="%", rangemode="tozero", showgrid=True, gridcolor="#F1F5F9")

    return counts, coverage


def render_job_results():
    """Show the outputs of an analysed video: details on left, evidence video on right."""
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.status == "completed").order_by(Job.created_at.desc()).limit(20).all()
        jobs = [j for j in jobs if _load_job_result(j.id)]
        if not jobs:
            st.info("Upload a video and run the analysis to review findings and evidence here.")
            return

        st.markdown("<hr class='fg-rule'>", unsafe_allow_html=True)
        st.markdown(section_title("Analysis results", "Review AI detections, deterministic risk scores and annotated video evidence."), unsafe_allow_html=True)

        active = st.session_state.get("active_job_id")
        ids = [j.id for j in jobs]
        idx = ids.index(active) if active in ids else 0
        job = st.selectbox(
            "Select analysed footage",
            jobs,
            index=idx,
            format_func=lambda j: f"{j.filename} · {j.created_at:%d %b %H:%M} · job {j.id[:8]}",
        )
        result = _load_job_result(job.id)
        if not result:
            return

        objects = result.get("objects")
        video_path = Path(result.get("annotated_video_path", ""))

        # ------------------------------------------------------------------
        # Two-Column Results Layout: Left = Details & Scores, Right = Video Evidence
        # ------------------------------------------------------------------
        res_left, res_right = st.columns([1.1, 1.3], gap="large")

        with res_right:
            st.markdown('<div class="fg-card-title" style="margin-bottom:8px;">Annotated CCTV Evidence Video</div>', unsafe_allow_html=True)
            if video_path.is_file():
                _show_evidence_video(video_path)
            st.caption(
                "Coloured outlines are per-object segmentation masks from the local YOLOE detector with persistent track IDs. "
                "White boxes marked VLM indicate Gemini's verified findings."
            )

            # Temporal telemetry charts
            if objects:
                timeline = objects.get("timeline") or []
                counts_fig, cov_fig = _timeline_charts(timeline) if timeline else (None, None)
                if counts_fig is not None:
                    st.markdown('<div class="fg-k" style="margin:12px 0 4px 0;">Objects in view over time</div>', unsafe_allow_html=True)
                    st.plotly_chart(counts_fig, use_container_width=True, config=_CHART_CONFIG)
                if cov_fig is not None:
                    st.markdown('<div class="fg-k" style="margin:12px 0 4px 0;">Garbage coverage curve</div>', unsafe_allow_html=True)
                    st.plotly_chart(cov_fig, use_container_width=True, config=_CHART_CONFIG)

            # Tracked objects table
            if objects and objects.get("objects"):
                tracked = objects.get("objects") or []
                rows = [
                    {
                        "Track": f"#{o['track_id']}",
                        "Object": o["label"],
                        "Category": CATEGORY_LABELS.get(o["category"], o["category"]),
                        "Waste type": WASTE_TYPE_LABELS.get(o.get("waste_type"), "") if o.get("waste_type") else "—",
                        "Seen": f"{o['first_sec']:.1f}s–{o['last_sec']:.1f}s",
                        "Frames": o["frames_seen"],
                        "Confidence": f"{o['max_confidence']:.0%}",
                    }
                    for o in tracked
                ]
                with st.expander(f"Tracked object inventory ({len(rows)})"):
                    st.dataframe(rows, hide_index=True, use_container_width=True)

        with res_left:
            st.markdown('<div class="fg-card-title" style="margin-bottom:8px;">Observed risk & civic findings</div>', unsafe_allow_html=True)

            # Scores (deterministic, from observed evidence only)
            s1, s2 = st.columns(2)
            s3, s4 = st.columns(2)
            _score_metric(s1, "Drainage risk", result.get("drainage_score"), result.get("drainage_band", ""))
            _score_metric(s2, "Garbage risk", result.get("garbage_score"), result.get("garbage_band", ""))
            _score_metric(s3, "Composite risk", result.get("composite_score"), result.get("composite_band", ""))
            s4.metric("Dumping violations", result.get("violations_count", 0), "officer queue", delta_color="off")

            sources = result.get("score_sources") or {}
            if sources:
                st.caption("Score inputs: " + " · ".join(f"{k.replace('_', ' ')}: {v}" for k, v in sources.items()))
            if result.get("drainage_score") is None:
                st.caption("Drainage is scored when Gemini detects a drain or manhole inlet (Pass C).")

            # Local detector KPI tiles
            if objects is not None:
                st.markdown('<div class="fg-k" style="margin:14px 0 6px 0;">Local detector telemetry</div>', unsafe_allow_html=True)
                frames = objects.get("frames_analyzed", 0)
                peak = objects.get("peak_in_frame")
                counts = objects.get("counts_by_category") or {}
                garbage_measured = objects.get("garbage_measured", True) is not False

                tiles = []
                if garbage_measured:
                    cov = objects.get("garbage_coverage")
                    cov_note = "90th percentile coverage"
                    if cov is None and objects.get("max_garbage_coverage") is not None:
                        cov, cov_note = objects.get("max_garbage_coverage"), "peak coverage"
                    tiles.append(_stat("Debris coverage", _pct(cov), cov_note))
                if garbage_measured and objects.get("garbage_frame_fraction") is not None:
                    tiles.append(_stat("Frames w/ trash", _pct(objects.get("garbage_frame_fraction")), f"of {frames} frames"))
                for cat in ("person", "vehicle", "drainage"):
                    label = CATEGORY_LABELS.get(cat, cat)
                    if peak is not None:
                        tiles.append(_stat(label, f"{peak.get(cat, 0)}", "peak in view"))
                    elif cat in counts:
                        tiles.append(_stat(label, f"{counts.get(cat, 0)}", "tracked"))

                if tiles:
                    t_cols = st.columns(min(3, len(tiles)))
                    for i, t_html in enumerate(tiles[:3]):
                        t_cols[i].markdown(t_html, unsafe_allow_html=True)

                # Waste stream chart
                shares = _waste_shares(objects.get("waste_breakdown") or {}) if garbage_measured else {}
                if shares:
                    st.markdown('<div class="fg-k" style="margin:12px 0 4px 0;">Waste stream composition</div>', unsafe_allow_html=True)
                    st.plotly_chart(_waste_chart(shares), use_container_width=True, config=_CHART_CONFIG)

            # Gemini findings list
            incidents = (
                db.query(Incident)
                .filter(Incident.job_id == job.id, Incident.subtype != "dumping_violation")
                .order_by(Incident.severity.desc())
                .all()
            )
            st.markdown('<div class="fg-k" style="margin:16px 0 6px 0;">Verified Gemini Findings</div>', unsafe_allow_html=True)
            if not incidents:
                st.info("No infrastructure hazards flagged by Gemini in this video.")
            for inc in incidents:
                with st.container(border=True):
                    img_col, txt_col = st.columns([1, 2])
                    frame = next((e.path for e in inc.evidences if e.kind == "annotated" and Path(e.path).is_file()), None)
                    if frame:
                        img_col.image(frame, use_container_width=True)
                    sent = {log.channel: log.status for log in inc.alerts}
                    txt_col.markdown(
                        f"**{inc.subtype.replace('_', ' ').capitalize()}** ({inc.type}) &middot; "
                        f"Severity {inc.severity}/5 &middot; at {inc.video_ts}"
                    )
                    txt_col.write(inc.description)
                    if inc.sewer_score:
                        txt_col.caption(f"Sewer overflow risk: {inc.sewer_score.score:.0f}/100 ({inc.sewer_score.band})")
                    if sent:
                        txt_col.caption("Alerts: " + ", ".join(f"{c} {s}" for c, s in sent.items()))
                    elif inc.severity >= settings.ALERT_MIN_SEVERITY:
                        txt_col.caption("Alert not sent: no alert channel configured.")

    finally:
        db.close()
