"""CCTV view: camera list and video analysis (Gemini findings + local detector)."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import plotly.graph_objects as go
import streamlit as st

from app.config import settings
from app.ui.pune_data import CCTV_CAMERAS
from app.core.pipeline import CivicEyePipeline
from app.db.session import SessionLocal
from app.db.models import Incident, Job
from app.core.detector import CATEGORY_LABELS, WASTE_TYPE_LABELS
from app.ui.components.charts import _style
from app.ui.components.styles import ACCENT, chip, icon, page_header, section_title, status_pill

_CHART_CONFIG = {"displayModeBar": False}


def render_cctv_monitoring():
    """Render the camera list and the video analysis workflow."""

    st.markdown(page_header(
        "CCTV analysis",
        "Run recorded camera footage through drain, garbage and dumping detection. Findings go to the priority queue.",
        eyebrow="Cameras",
        meta=[f"<b>{len(CCTV_CAMERAS[:3])}</b> cameras assigned", "Video upload and review"],
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
            "Analyse a video",
            "Gemini finds drainage, garbage and road problems and anyone dumping waste. A local YOLOE model outlines "
            "and tracks objects frame by frame and measures how much of the frame garbage covers.",
        ), unsafe_allow_html=True)

        sample_ganga_path = settings.UPLOADS_DIR / "ganga.mp4"
        has_sample = sample_ganga_path.exists()

        col_src1, col_src2 = st.columns([1.5, 1], gap="large")
        with col_src1:
            uploaded_file = st.file_uploader("Video file (.mp4, .mov, .webm)", type=["mp4", "mov", "webm"])
            if has_sample:
                use_sample = st.checkbox("Use the sample clip (Ganga Dham conduit)", value=True if not uploaded_file else False)
            else:
                use_sample = False

            cam_choice = st.selectbox("Camera", [c["name"] + f" ({c['id']})" for c in CCTV_CAMERAS[:3]])
            custom_gps = st.text_input("Camera GPS coordinates", value="18.4850, 73.8650")

        with col_src2:
            steps = [
                ("Gemini, pass A", "Drains, manholes, garbage, potholes and other road hazards"),
                ("Gemini, pass C", "Water level and blockage at each drain found"),
                ("Local YOLOE", "Object masks and tracking; garbage coverage by waste stream"),
                ("Gemini, pass B", "People dumping garbage, vehicle and number plate"),
            ]
            rows = "".join(
                f'<div style="display:flex;gap:10px;padding:8px 0;border-top:1px solid #EEF1F5;">'
                f'<span class="fg-mono" style="font-size:11px;color:#0A7C8F;width:18px;">{i}</span>'
                f'<div><div style="font-size:12.5px;font-weight:600;color:#0B1220;">{t}</div>'
                f'<div style="font-size:12px;color:#64708A;">{d}</div></div></div>'
                for i, (t, d) in enumerate(steps, 1)
            )
            st.markdown(f'<div class="fg-card"><div class="fg-k" style="margin-bottom:4px;">What runs on the video</div>{rows}</div>', unsafe_allow_html=True)
            run_violator_pass = st.checkbox("Run pass B (dumping violations)", value=True)

        execute_clicked = st.button("Run analysis", type="primary", use_container_width=True)

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
                with st.status("Analysing video", expanded=True) as status:
                    status.write(f"Source: `{target_video_path.name}` ({target_video_path.stat().st_size / (1024*1024):.2f} MB)")
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
                    except Exception as e:
                        status.update(label="Analysis failed", state="error")
                        st.error(f"Video analysis failed: {e}")
            else:
                st.warning("Upload a video file or select the sample clip.")

        render_job_results()


def _load_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    path = settings.EVIDENCE_DIR / job_id / "result.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _video_aspect(path: Path) -> Optional[float]:
    """Width / height of a video file, or None if it cannot be read."""
    try:
        import cv2

        cap = cv2.VideoCapture(str(path))
        w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        cap.release()
        return (w / h) if w and h else None
    except Exception:
        return None


def _show_evidence_video(path: Path) -> None:
    """Show the evidence video so the whole frame fits on screen, portrait or landscape.

    A centre column sized from the aspect ratio keeps portrait clips narrow; the
    .fg-evidence CSS (max-height 70vh, object-fit contain) guarantees it fits any viewport.
    """
    aspect = _video_aspect(path) or 16 / 9
    # Column share that gives roughly 640px of height on a ~1270px wide content area.
    share = min(1.0, max(0.25, aspect * 0.5))
    with st.container(key="fg_evidence_video"):
        if share >= 0.98:
            st.video(str(path))
        else:
            side = (1 - share) / 2
            _, mid, _ = st.columns([side, share, side])
            with mid:
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
    """Return waste-stream shares (0-1). New results store area fractions; older ones store counts."""
    waste = {k: v for k, v in waste.items() if v is not None}
    total = sum(float(v) for v in waste.values())
    if total <= 0:
        return {}
    if total <= 1.01:
        return {k: float(v) for k, v in waste.items()}
    return {k: float(v) / total for k, v in waste.items()}


def _waste_chart(shares: Dict[str, float]) -> go.Figure:
    items = sorted(shares.items(), key=lambda kv: kv[1])
    labels = [WASTE_TYPE_LABELS.get(k, k) for k, _ in items]
    vals = [v * 100 for _, v in items]
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h",
        marker=dict(color=ACCENT, cornerradius=3),
        text=[f"{v:.0f}%" for v in vals], textposition="outside", cliponaxis=False,
        textfont=dict(family="JetBrains Mono", size=11, color="#334155"),
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    _style(fig, max(140, 46 * len(labels) + 40), dict(t=6, b=24, l=10, r=40))
    fig.update_xaxes(range=[0, 110], ticksuffix="%", showgrid=True, gridcolor="#EEF1F5")
    fig.update_yaxes(tickfont=dict(family="Inter", size=12, color="#334155"), showgrid=False)
    return fig


def _timeline_charts(timeline):
    secs = [row.get("sec", i) for i, row in enumerate(timeline)]
    cats = sorted({k for row in timeline for k in row if k not in ("sec", "garbage_coverage")})
    palette = ["#0A7C8F", "#0B1220", "#C25A06", "#7C8BA1", "#14784F", "#9A7200", "#C8281C"]
    counts = None
    if cats:
        counts = go.Figure()
        for i, c in enumerate(cats):
            counts.add_trace(go.Scatter(
                x=secs, y=[row.get(c, 0) for row in timeline], name=CATEGORY_LABELS.get(c, c), mode="lines",
                line=dict(color=palette[i % len(palette)], width=1.8, shape="hv"),
                hovertemplate=f"{CATEGORY_LABELS.get(c, c)}: %{{y}}<extra></extra>",
            ))
        _style(counts, 220, dict(t=24, b=30, l=36, r=10))
        counts.update_xaxes(title="Seconds into video")
        counts.update_yaxes(title="In view", rangemode="tozero")
    coverage = None
    if any("garbage_coverage" in row for row in timeline):
        coverage = go.Figure(go.Scatter(
            x=secs, y=[(row.get("garbage_coverage") or 0) * 100 for row in timeline], mode="lines",
            line=dict(color="#C25A06", width=1.8), fill="tozeroy", fillcolor="rgba(194,90,6,0.10)",
            hovertemplate="%{x}s: %{y:.1f}% of frame<extra></extra>", name="Garbage coverage",
        ))
        _style(coverage, 200, dict(t=10, b=30, l=40, r=10))
        coverage.update_xaxes(title="Seconds into video")
        coverage.update_yaxes(title="% of frame", ticksuffix="%", rangemode="tozero")
    return counts, coverage


def render_job_results():
    """Show the real outputs of an analysed video: evidence video, objects, garbage coverage, scores."""
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.status == "completed").order_by(Job.created_at.desc()).limit(20).all()
        jobs = [j for j in jobs if _load_job_result(j.id)]
        if not jobs:
            st.info("Upload a video and run the analysis to see detections here.")
            return

        st.markdown("<hr class='fg-rule'>", unsafe_allow_html=True)
        st.markdown(section_title("Results", "Choose an analysed video to review its evidence and scores."), unsafe_allow_html=True)
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
            _show_evidence_video(video_path)
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

        # Local detector output
        st.markdown(section_title("Local detector"), unsafe_allow_html=True)
        if objects is None:
            st.warning("The local detector did not run for this video, so only Gemini's findings are available.")
        else:
            frames = objects.get("frames_analyzed", 0)
            min_frames = objects.get("min_frames", 2)
            peak = objects.get("peak_in_frame")
            counts = objects.get("counts_by_category") or {}

            garbage_measured = objects.get("garbage_measured", True) is not False
            tiles = []
            if garbage_measured:
                cov = objects.get("garbage_coverage")
                cov_note = "90th percentile of frame area covered"
                if cov is None and objects.get("max_garbage_coverage") is not None:
                    cov, cov_note = objects.get("max_garbage_coverage"), "peak frame area covered"
                tiles.append(_stat("Garbage coverage", _pct(cov), cov_note))
            if garbage_measured and objects.get("garbage_frame_fraction") is not None:
                tiles.append(_stat("Frames with garbage", _pct(objects.get("garbage_frame_fraction")), f"of {frames} analysed frames"))
            for cat in ("person", "vehicle", "drainage"):
                label = CATEGORY_LABELS.get(cat, cat)
                if peak is not None:
                    tiles.append(_stat(label, f"{peak.get(cat, 0)}", "most in view in one frame"))
                elif cat in counts:
                    tiles.append(_stat(label, f"{counts.get(cat, 0)}", "tracks (may overcount)"))
            if tiles:
                cols = st.columns(len(tiles))
                for col, html in zip(cols, tiles):
                    col.markdown(html, unsafe_allow_html=True)
            if not garbage_measured:
                st.info(
                    "Garbage not measured by the local detector for this video (Gemini garbage examples unavailable); "
                    "garbage score uses Gemini's severity rating instead."
                )

            exemplars = objects.get("garbage_exemplar_frames")
            detector_caption = (
                f"{objects.get('detector', 'detector')} · {frames} frames analysed · "
                f"tracks seen in fewer than {min_frames} analysed frames are dropped as flicker"
            )
            if exemplars:
                detector_caption += f" · garbage examples taken from {exemplars} frames Gemini marked as garbage"
            st.caption(detector_caption + ".")

            w_col, t_col = st.columns([1, 1.4], gap="large")
            with w_col:
                st.markdown('<div class="fg-k" style="margin:8px 0 4px 0;">Share of garbage area by waste stream</div>', unsafe_allow_html=True)
                shares = _waste_shares(objects.get("waste_breakdown") or {}) if garbage_measured else {}
                if not garbage_measured:
                    st.caption("Not measured for this video.")
                elif shares:
                    st.plotly_chart(_waste_chart(shares), use_container_width=True, config=_CHART_CONFIG)
                else:
                    st.caption("No garbage measured.")
            with t_col:
                timeline = objects.get("timeline") or []
                counts_fig, cov_fig = _timeline_charts(timeline) if timeline else (None, None)
                if not garbage_measured:
                    cov_fig = None
                if counts_fig is not None:
                    st.markdown('<div class="fg-k" style="margin:8px 0 4px 0;">Objects in view over time</div>', unsafe_allow_html=True)
                    st.plotly_chart(counts_fig, use_container_width=True, config=_CHART_CONFIG)
                if cov_fig is not None:
                    st.markdown('<div class="fg-k" style="margin:8px 0 4px 0;">Garbage coverage over time</div>', unsafe_allow_html=True)
                    st.plotly_chart(cov_fig, use_container_width=True, config=_CHART_CONFIG)

            tracked = objects.get("objects") or []
            if not tracked:
                st.info(f"No objects were tracked across {frames} analysed frames.")
            else:
                rows = [
                    {
                        "Track": f"#{o['track_id']}",
                        "Object": o["label"],
                        "Group": CATEGORY_LABELS.get(o["category"], o["category"]),
                        "Waste stream": WASTE_TYPE_LABELS.get(o.get("waste_type"), "") if o.get("waste_type") else "",
                        "Seen (s)": f"{o['first_sec']:.1f}–{o['last_sec']:.1f}",
                        "Frames": o["frames_seen"],
                        "Max confidence": round(o["max_confidence"], 2),
                    }
                    for o in tracked
                ]
                with st.expander(f"Tracked objects ({len(rows)})"):
                    st.dataframe(rows, hide_index=True, use_container_width=True)
                    st.caption("A person can appear under more than one track ID when the camera pans or people overlap.")

        # Gemini findings
        incidents = (
            db.query(Incident)
            .filter(Incident.job_id == job.id, Incident.subtype != "dumping_violation")
            .order_by(Incident.severity.desc())
            .all()
        )
        st.markdown(section_title("Gemini findings"), unsafe_allow_html=True)
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
                    f"**{inc.subtype.replace('_', ' ').capitalize()}** ({inc.type}) · severity {inc.severity}/5 · "
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
