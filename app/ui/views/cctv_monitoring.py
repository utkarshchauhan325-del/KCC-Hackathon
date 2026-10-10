"""CCTV view: assigned cameras and video analysis (Gemini findings + local detector).

Layout: video on the right, everything about that video on the left.
"""

import json
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional

import plotly.graph_objects as go
import streamlit as st

from app.config import settings
from app.core.detector import CATEGORY_LABELS, WASTE_TYPE_LABELS
from app.core.pipeline import CivicEyePipeline
from app.db.models import Incident, Job
from app.db.session import SessionLocal
from app.ui.components.charts import _style
from app.ui.components.crew_dispatch import render_crew_dispatch_widget
from app.ui.components.evidence_frames import job_key_frames, latest_job_for_video, render_frame_gallery
from app.ui.components.styles import icon, page_header, section_title, status_color, status_pill
from app.ui.pune_data import ASSIGNED_CAMERAS, CCTV_CAMERAS, PUNE_LOCATIONS, get_weather_adjusted_locations, location_for_job

_CHART_CONFIG = {"displayModeBar": False}

# Formats OpenCV can decode. Browsers only preview mp4 / webm / mov / m4v directly.
VIDEO_TYPES = ["mp4", "mov", "webm", "m4v", "avi", "mkv", "mpeg", "mpg", "3gp", "wmv", "flv", "ts"]
BROWSER_PLAYABLE = {".mp4", ".webm", ".mov", ".m4v"}

WASTE_STREAM_COLORS = {
    "dry_plastic": "#0284C7",
    "dry_paper": "#6366F1",
    "wet_organic": "#059669",
    "construction": "#D97706",
    "e_waste": "#8B5CF6",
    "mixed": "#64748B",
}
CATEGORY_COLORS = {
    "garbage": "#C2410C",
    "person": "#059669",
    "vehicle": "#6366F1",
    "drainage": "#0A7C8F",
    "road": "#D97706",
    "bin": "#8B5CF6",
    "plate": "#DB2777",
}
_BAND_LEVEL = {"Critical": "Critical", "High": "High", "Watch": "Medium", "Medium": "Medium", "Low": "Low"}


# ---------------------------------------------------------------------------
# Areas the footage can be tagged with
# ---------------------------------------------------------------------------
def _all_areas() -> List[Dict[str, Any]]:
    """Assigned cameras first, then every monitored location and the remaining cameras."""
    areas: List[Dict[str, Any]] = []
    by_id = {l["id"]: l for l in PUNE_LOCATIONS}
    for cam in ASSIGNED_CAMERAS:
        loc = by_id.get(cam["location_id"], {})
        areas.append({
            "label": f"{cam['name']} ({cam['id']})",
            "name": loc.get("name", cam["name"]),
            "ward": loc.get("ward", f"{cam['zone']} corridor"),
            "zone": cam["zone"],
            "lat": cam["lat"],
            "lng": cam["lng"],
            "drain_type": loc.get("drain_type", "Stormwater drain"),
            "risk_level": _BAND_LEVEL.get(cam["risk_level"], "Medium"),
            "source": "Assigned camera",
        })
    for loc in sorted(PUNE_LOCATIONS, key=lambda l: (l["zone"], l["name"])):
        areas.append({
            "label": f"{loc['name']} · {loc['ward']}",
            "name": loc["name"],
            "ward": loc["ward"],
            "zone": loc["zone"],
            "lat": loc["lat"],
            "lng": loc["lng"],
            "drain_type": loc["drain_type"],
            "risk_level": loc["risk_level"],
            "source": "Monitored location",
        })
    for cam in CCTV_CAMERAS:
        if cam in ASSIGNED_CAMERAS:
            continue
        areas.append({
            "label": f"{cam['name']} ({cam['id']})",
            "name": cam["name"],
            "ward": f"{cam['zone']} corridor",
            "zone": cam["zone"],
            "lat": cam["lat"],
            "lng": cam["lng"],
            "drain_type": "Fixed CCTV view",
            "risk_level": cam["risk_level"],
            "source": "City camera",
        })
    return areas


def _video_info(path: Path) -> Dict[str, Any]:
    """Duration, resolution and frame rate, or {} if OpenCV cannot read the file."""
    try:
        import cv2

        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        cap.release()
        if not (w and h):
            return {}
        return {"duration": frames / fps if fps else None, "width": w, "height": h, "fps": fps}
    except Exception:
        return {}


def _fmt_duration(sec: Optional[float]) -> str:
    if not sec:
        return "n/a"
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def _video_panel(path: Path, title: str, note: str, key: str) -> None:
    """Dark title bar + player, sized so portrait and landscape clips both fit."""
    st.markdown(
        f'<div class="fg-video-bar"><span class="fg-rec"><i></i><b>{escape(title)}</b></span><span>{escape(note)}</span></div>',
        unsafe_allow_html=True,
    )
    with st.container(key=f"fgvideo_{key}"):
        st.video(str(path))


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render_cctv_monitoring():
    """Render the camera list and the video analysis workflow."""
    st.markdown(page_header(
        "CCTV analysis",
        "Run camera footage through drain, garbage and dumping detection. Key frames and findings go to the priority queue automatically.",
        eyebrow="Cameras",
        meta=[f"<b>{len(ASSIGNED_CAMERAS)}</b> cameras assigned", f"<b>{len(_all_areas())}</b> areas", "Video upload and review"],
    ), unsafe_allow_html=True)

    tab_upload, tab_grid = st.tabs(["Analyse video", "Cameras"])
    with tab_grid:
        _render_camera_grid()
    with tab_upload:
        _render_upload()
        render_job_results()


def _render_camera_grid() -> None:
    st.markdown(section_title("Assigned cameras"), unsafe_allow_html=True)
    locations = {l["id"]: l for l in get_weather_adjusted_locations()}
    db = SessionLocal()
    try:
        cols = st.columns(len(ASSIGNED_CAMERAS), gap="medium")
        for col, cam in zip(cols, ASSIGNED_CAMERAS):
            loc = locations.get(cam["location_id"], {})
            job = latest_job_for_video(db, cam.get("video", ""))
            frames = job_key_frames(job) if job else []
            with col:
                level = _BAND_LEVEL.get(cam["risk_level"], "Medium")
                st.markdown(
                    f'<div class="fg-card" style="padding:14px 14px 4px 14px;margin-bottom:8px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">'
                    f'<div style="min-width:0;"><div style="font-size:14px;font-weight:600;color:#0B1220;">{cam["name"]}</div>'
                    f'<div class="fg-mono" style="font-size:11px;color:#64708A;">{cam["id"]} &middot; {loc.get("name", "")}</div></div>'
                    f'{status_pill(level, cam["risk_level"])}</div></div>',
                    unsafe_allow_html=True,
                )
                if frames:
                    with st.container(key=f"fgframe_cam_{cam['id']}"):
                        st.image(frames[0][0], use_container_width=True)
                else:
                    st.markdown(
                        f'<div class="fg-noframe">{icon("camera", 22)}<span>No analysed video yet</span>'
                        f'<span class="fg-mono" style="font-size:10.5px;">{cam["lat"]}, {cam["lng"]}</span></div>',
                        unsafe_allow_html=True,
                    )
                drainage = "Not assessed" if cam["drainage_score"] is None else f"{cam['drainage_score']}/100"
                outlook = loc.get("overflow_outlook", "n/a")
                st.markdown(
                    f'<div class="fg-card" style="padding:12px 14px;margin-top:8px;">'
                    f'{_score_tile_inner("Composite risk", cam["composite_score"], cam["risk_level"])}'
                    f'<div class="fg-kv" style="margin-top:12px;grid-template-columns:1fr 1fr;">'
                    f'<div><span class="fg-k">Drainage</span><span class="fg-v mono">{drainage}</span></div>'
                    f'<div><span class="fg-k">Garbage</span><span class="fg-v mono">{cam["garbage_score"]}/100</span></div>'
                    f'<div><span class="fg-k">Garbage cover</span><span class="fg-v mono">{cam["garbage_coverage_pct"]}%</span></div>'
                    f'<div><span class="fg-k">Drain blockage</span><span class="fg-v mono">{cam["blockage_index"]}%</span></div>'
                    f'<div><span class="fg-k">Dumping violations</span><span class="fg-v mono">{cam["violations"]}</span></div>'
                    f'<div><span class="fg-k">Overflow (24 h)</span><span class="fg-v" style="font-size:12px;">{outlook}</span></div>'
                    f'</div>'
                    f'<div style="font-size:12px;color:#334155;margin-top:10px;padding-top:8px;border-top:1px solid #F1F5F9;">'
                    f'<span class="fg-k">Last finding</span><br>{cam["ai_status"]}</div></div>',
                    unsafe_allow_html=True,
                )
    finally:
        db.close()


def _render_upload() -> None:
    areas = _all_areas()
    zones = ["All zones"] + sorted({a["zone"] for a in areas})

    col_details, col_video = st.columns([1, 1.25], gap="large")

    # Right: drag and drop + preview
    with col_video:
        st.markdown(section_title("Footage"), unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Video file",
            type=VIDEO_TYPES,
            help="MP4, MOV, WEBM, M4V, AVI, MKV, MPEG, 3GP, WMV, FLV or TS, up to "
                 f"{settings.MAX_UPLOAD_SIZE_MB} MB.",
            label_visibility="collapsed",
        )
        saved = sorted(
            (p for p in settings.UPLOADS_DIR.iterdir() if p.suffix.lower().lstrip(".") in VIDEO_TYPES),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        target: Optional[Path] = None
        if uploaded:
            target = settings.UPLOADS_DIR / Path(uploaded.name.replace(" ", "_")).name
            if not target.exists() or target.stat().st_size != uploaded.size:
                target.write_bytes(uploaded.getbuffer())
        elif saved:
            pick = st.selectbox("Or choose an uploaded video", [p.name for p in saved])
            target = settings.UPLOADS_DIR / pick

        if target and target.is_file():
            size_mb = target.stat().st_size / (1024 * 1024)
            if target.suffix.lower() in BROWSER_PLAYABLE:
                _video_panel(target, target.name, f"{size_mb:.1f} MB", "preview")
            else:
                st.markdown(
                    f'<div class="fg-dropzone-empty">{icon("camera", 28)}<b style="color:#334155;">{escape(target.name)}</b>'
                    f'<span style="font-size:12px;">Browsers cannot preview {target.suffix.upper()} files. '
                    f'The analysis still runs, and the evidence video is converted to MP4.</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                f'<div class="fg-dropzone-empty">{icon("camera", 30)}<b style="color:#334155;">No footage selected</b>'
                f'<span style="font-size:12px;">Drop a video above to preview it here.</span></div>',
                unsafe_allow_html=True,
            )

    # Left: where the video is from, what it is, what will run
    with col_details:
        st.markdown(section_title("Video details"), unsafe_allow_html=True)
        z_col, a_col = st.columns([1, 2.2])
        zone = z_col.selectbox("Zone", zones)
        options = [a for a in areas if zone == "All zones" or a["zone"] == zone]
        # A camera's own footage defaults to that camera
        own_cam = next((c for c in ASSIGNED_CAMERAS if target and c.get("video") == target.name), None)
        default = next((i for i, a in enumerate(options) if own_cam and a["label"].endswith(f"({own_cam['id']})")), 0)
        area = a_col.selectbox(
            f"Camera or area ({len(options)})",
            options,
            index=default,
            format_func=lambda a: a["label"],
            key=f"area_{zone}_{target.name if target else ''}",
        )
        gps = st.text_input("Camera GPS", value=f"{area['lat']:.4f}, {area['lng']:.4f}", key=f"gps_{area['label']}")

        info = _video_info(target) if target and target.is_file() else {}
        fps_note = f" @ {info['fps']:.0f} fps" if info.get("fps") else ""
        file_rows = '<div><span class="fg-k">File</span><span class="fg-v">None selected</span></div>'
        if target and target.is_file():
            file_rows = (
                f'<div><span class="fg-k">File</span><span class="fg-v mono" style="font-size:12px;overflow:hidden;text-overflow:ellipsis;">{escape(target.name)}</span></div>'
                f'<div><span class="fg-k">Size</span><span class="fg-v mono">{target.stat().st_size / (1024 * 1024):.1f} MB</span></div>'
                f'<div><span class="fg-k">Duration</span><span class="fg-v mono">{_fmt_duration(info.get("duration"))}</span></div>'
                f'<div><span class="fg-k">Resolution</span><span class="fg-v mono">{info.get("width", "?")} x {info.get("height", "?")}'
                f'{fps_note}</span></div>'
            )
        st.markdown(
            f'<div class="fg-card" style="padding:14px 16px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px;">'
            f'<span style="font-size:14px;font-weight:600;color:#0B1220;">{escape(area["name"])}</span>{status_pill(area["risk_level"])}</div>'
            f'<div style="font-size:12px;color:#64708A;margin-bottom:10px;">{escape(area["ward"])} &middot; {area["zone"]} zone &middot; '
            f'{escape(area["drain_type"])} &middot; {area["source"]}</div>'
            f'<div class="fg-kv" style="grid-template-columns:1fr 1fr;">{file_rows}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


        run_pass_b = True

        if st.button("Run analysis", type="primary", use_container_width=True, disabled=target is None):
            with st.status("Analysing video", expanded=True) as status:
                status.write(f"Source: `{target.name}` ({target.stat().st_size / (1024 * 1024):.1f} MB) · {area['name']}")
                try:
                    result = CivicEyePipeline().process_video(
                        video_path=target,
                        source_gps=gps,
                        run_pass_b=run_pass_b,
                        progress_cb=lambda msg: status.write(msg),
                    )
                    status.update(label="Analysis complete", state="complete", expanded=False)
                    st.session_state["active_job_id"] = result["job_id"]
                    st.toast("Analysis complete. Key frames were added to the priority queue.")
                    st.rerun()
                except Exception as e:
                    status.update(label="Analysis failed", state="error")
                    st.error(f"Video analysis failed: {e}")


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
def _load_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    path = settings.EVIDENCE_DIR / job_id / "result.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _score_tile_inner(label: str, score: Optional[float], band: str) -> str:
    level = _BAND_LEVEL.get(band, "Medium")
    color = status_color(level) if score is not None else "#94A3B8"
    value = "Not assessed" if score is None else f'{score:.0f}<small> / 100</small>'
    pill = status_pill(level, band) if score is not None else ""
    width = 0 if score is None else max(2, min(100, score))
    return (
        f'<div class="fg-score-top"><span class="fg-score-label">{label}</span>{pill}</div>'
        f'<div class="fg-score-val" style="{"font-size:16px;color:#94A3B8;" if score is None else ""}">{value}</div>'
        f'<div class="fg-bar"><span style="width:{width}%;background:{color};"></span></div>'
    )


def _score_tile(label: str, score: Optional[float], band: str, note: str = "") -> str:
    note_html = f'<div class="fg-score-note">{note}</div>' if note else ""
    return f'<div class="fg-score">{_score_tile_inner(label, score, band)}{note_html}</div>'


def _stat_tile(label: str, value: str, note: str = "") -> str:
    return (
        f'<div class="fg-score"><div class="fg-score-label">{label}</div>'
        f'<div class="fg-score-val" style="font-size:20px;margin-bottom:2px;">{value}</div>'
        f'<div class="fg-score-note" style="margin-top:0;">{note}</div></div>'
    )


def _waste_shares(waste: Dict[str, float]) -> Dict[str, float]:
    """Waste-stream shares (0-1). New results store area fractions; older ones store counts."""
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
        marker=dict(color=[WASTE_STREAM_COLORS.get(k, "#64748B") for k, _ in items], cornerradius=5),
        text=[f"<b>{v:.0f}%</b>" for v in vals], textposition="outside", cliponaxis=False,
        textfont=dict(family="JetBrains Mono", size=11, color="#334155"),
        hovertemplate="%{y}: %{x:.1f}% of garbage area<extra></extra>",
    ))
    _style(fig, max(150, 40 * len(labels) + 40), dict(t=6, b=20, l=10, r=44))
    fig.update_layout(bargap=0.38, showlegend=False)
    fig.update_xaxes(range=[0, 115], showticklabels=False, showgrid=False)
    fig.update_yaxes(tickfont=dict(family="Inter", size=12, color="#334155"), showgrid=False)
    return fig


def _timeline_charts(timeline):
    secs = [row.get("sec", i) for i, row in enumerate(timeline)]
    cats = sorted({k for row in timeline for k in row if k not in ("sec", "garbage_coverage")})
    counts = None
    if cats:
        counts = go.Figure()
        for c in cats:
            color = CATEGORY_COLORS.get(c, "#64748B")
            counts.add_trace(go.Scatter(
                x=secs, y=[row.get(c, 0) for row in timeline], name=CATEGORY_LABELS.get(c, c), mode="lines",
                line=dict(color=color, width=2, shape="hv"),
                hovertemplate=f"{CATEGORY_LABELS.get(c, c)}: %{{y}} at %{{x}}s<extra></extra>",
            ))
        _style(counts, 230, dict(t=34, b=34, l=36, r=10))
        counts.update_layout(hovermode="x unified")
        counts.update_xaxes(title="Seconds into video", showgrid=True, gridcolor="#F1F5F9")
        counts.update_yaxes(title="In view", rangemode="tozero")
    coverage = None
    if any("garbage_coverage" in row for row in timeline):
        y = [(row.get("garbage_coverage") or 0) * 100 for row in timeline]
        coverage = go.Figure(go.Scatter(
            x=secs, y=y, mode="lines",
            line=dict(color="#C2410C", width=2, shape="spline", smoothing=0.6),
            fill="tozeroy", fillcolor="rgba(194,65,12,0.12)",
            hovertemplate="%{x}s: %{y:.1f}% of frame<extra></extra>", name="Garbage coverage",
        ))
        peak = max(y, default=0)
        if peak > 0:
            i = y.index(peak)
            coverage.add_annotation(x=secs[i], y=peak, text=f"peak {peak:.0f}%", showarrow=True, arrowhead=0, ax=0, ay=-22,
                                    font=dict(size=10.5, color="#C2410C", family="JetBrains Mono"))
        _style(coverage, 200, dict(t=24, b=34, l=40, r=10))
        coverage.update_layout(showlegend=False)
        coverage.update_xaxes(title="Seconds into video", showgrid=True, gridcolor="#F1F5F9")
        coverage.update_yaxes(title="% of frame", ticksuffix="%", rangemode="tozero")
    return counts, coverage


def render_job_results():
    """Show an analysed video: evidence video and key frames on the right, scores and findings on the left."""
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.status == "completed").order_by(Job.created_at.desc()).limit(20).all()
        jobs = [j for j in jobs if _load_job_result(j.id)]
        if not jobs:
            st.info("Upload a video and run the analysis to see detections here.")
            return

        st.markdown("<hr class='fg-rule'>", unsafe_allow_html=True)
        head, pick = st.columns([1.3, 1], vertical_alignment="bottom")
        head.markdown(section_title("Results"), unsafe_allow_html=True)
        active = st.session_state.get("active_job_id")
        by_id = {j.id: j for j in jobs}
        ids = list(by_id)
        job_id = pick.selectbox(
            "Analysed video",
            ids,
            index=ids.index(active) if active in ids else 0,
            format_func=lambda i: f"{by_id[i].filename} · {by_id[i].created_at:%d %b %H:%M}",
            label_visibility="collapsed",
        )
        job = by_id[job_id]
        result = _load_job_result(job.id)
        objects = result.get("objects")
        site = location_for_job(job.filename, job.source_gps)
        incidents = (
            db.query(Incident)
            .filter(Incident.job_id == job.id, Incident.subtype != "dumping_violation")
            .order_by(Incident.severity.desc())
            .all()
        )

        left, right = st.columns([1, 1.25], gap="large")

        # Right: the evidence video and the frames that went to the queue
        with right:
            video_path = Path(result["annotated_video_path"])
            if video_path.is_file():
                _video_panel(video_path, job.filename, f"{site['name']} · job {job.id[:8]}", f"result_{job.id[:8]}")
            st.caption(
                "Coloured outlines are per-object masks from the local detector, each with a track ID that follows it "
                "across frames. White boxes marked VLM are LLM model findings."
            )
            st.markdown(section_title("Key frames"), unsafe_allow_html=True)
            render_frame_gallery(job_key_frames(job), key=f"res_{job.id[:8]}", columns=2)

        # Left: everything about the video
        with left:
            st.markdown(
                f'<div class="fg-card" style="padding:12px 16px;">'
                f'<div class="fg-k">Location</div><div style="font-size:15px;font-weight:600;color:#0B1220;margin-top:2px;">{site["name"]}</div>'
                f'<div style="font-size:12px;color:#64708A;">{site["ward"]} &middot; {site["zone"]} zone &middot; '
                f'GPS {escape(job.source_gps or "not given")} &middot; analysed {job.created_at:%d %b %Y, %H:%M}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="fg-grid fg-grid-2">'
                + _score_tile("Composite risk", result.get("composite_score"), result.get("composite_band", ""))
                + _score_tile("Drainage risk", result.get("drainage_score"), result.get("drainage_band", ""),
                              "" if result.get("drainage_score") is not None else "Scored only when LLM model finds and inspects a drain")
                + _score_tile("Garbage risk", result.get("garbage_score"), result.get("garbage_band", ""))
                + _stat_tile("Dumping violations", str(result.get("violations_count", 0)), "waiting for officer review in the queue")
                + "</div>",
                unsafe_allow_html=True,
            )


            if objects is None:
                st.warning("The local detector did not run for this video, so only LLM model findings are available.")
            else:
                _render_detector_summary(objects)

            st.markdown(section_title("LLM model findings", f"{len(incidents)} issue(s), most severe first"), unsafe_allow_html=True)
            if not incidents:
                st.info("LLM model reported no drainage, garbage or road issues in this video.")
            for inc in incidents:
                sev_level = "Critical" if inc.severity >= 5 else ("High" if inc.severity >= 4 else "Medium")
                sent = {log.channel: log.status for log in inc.alerts}
                alert_note = (
                    "Alerts: " + ", ".join(f"{c} {s}" for c, s in sent.items()) if sent
                    else ("Alert not sent: no alert channel configured." if inc.severity >= settings.ALERT_MIN_SEVERITY else "")
                )
                sewer = f" &middot; sewer overflow {inc.sewer_score.score:.0f}/100" if inc.sewer_score else ""
                alert_html = f'<div style="font-size:11.5px;color:#94A3B8;margin-top:6px;">{alert_note}</div>' if alert_note else ""
                st.markdown(
                    f'<div class="fg-card" style="padding:12px 14px;box-shadow:inset 3px 0 0 {status_color(sev_level)}, var(--fg-shadow);">'
                    f'<div style="display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;">'
                    f'<span style="font-size:13.5px;font-weight:600;color:#0B1220;">{inc.subtype.replace("_", " ").capitalize()}</span>'
                    f'{status_pill(sev_level, f"Severity {inc.severity}/5")}</div>'
                    f'<div class="fg-mono" style="font-size:11px;color:#64708A;margin:2px 0 6px;">{inc.type} &middot; at {inc.video_ts} &middot; '
                    f'confidence {inc.confidence:.0%}{sewer}</div>'
                    f'<div style="font-size:13px;color:#334155;line-height:1.5;">{escape(inc.description)}</div>'
                    f'{alert_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Full width: charts and object table
        if objects is not None:
            _render_detector_charts(objects)

        st.markdown(section_title("Send a crew", f"Dispatch machinery and an engineer to {site['name']}."), unsafe_allow_html=True)
        render_crew_dispatch_widget(
            location_name=site["name"],
            key_prefix=f"cctv_{job.id[:8]}",
            suggested_machinery=(
                "High Pressure Silt Jetting & Suction Tanker"
                if any(inc.type == "drainage" for inc in incidents)
                else "Solid Waste Rapid Clearance Unit"
            ),
            zone=site["zone"],
            header_title=None,
        )
    finally:
        db.close()


def _render_detector_summary(objects: Dict[str, Any]) -> None:
    frames = objects.get("frames_analyzed", 0)
    peak = objects.get("peak_in_frame")
    counts = objects.get("counts_by_category") or {}
    garbage_measured = objects.get("garbage_measured", True) is not False

    tiles = []
    if garbage_measured:
        cov = objects.get("garbage_coverage")
        note = "90th percentile of frame area"
        if cov is None and objects.get("max_garbage_coverage") is not None:
            cov, note = objects.get("max_garbage_coverage"), "peak frame area"
        tiles.append(_stat_tile("Garbage coverage", _pct(cov), note))
        if objects.get("garbage_frame_fraction") is not None:
            tiles.append(_stat_tile("Frames with garbage", _pct(objects.get("garbage_frame_fraction")), f"of {frames} analysed frames"))
    for cat in ("person", "vehicle", "drainage"):
        label = CATEGORY_LABELS.get(cat, cat)
        if peak is not None:
            tiles.append(_stat_tile(label, str(peak.get(cat, 0)), "most in one frame"))
        elif cat in counts:
            tiles.append(_stat_tile(label, str(counts.get(cat, 0)), "tracks (may overcount)"))

    st.markdown(section_title("Local detector", f"{objects.get('detector', 'YOLOE')} &middot; {frames} frames analysed"),
                unsafe_allow_html=True)
    if tiles:
        st.markdown(f'<div class="fg-grid fg-grid-3">{"".join(tiles)}</div>', unsafe_allow_html=True)
    if not garbage_measured:
        st.caption("Garbage was not measured by the local detector for this video, so the garbage score uses LLM model severity rating.")


def _render_detector_charts(objects: Dict[str, Any]) -> None:
    garbage_measured = objects.get("garbage_measured", True) is not False
    timeline = objects.get("timeline") or []
    counts_fig, cov_fig = _timeline_charts(timeline) if timeline else (None, None)
    shares = _waste_shares(objects.get("waste_breakdown") or {}) if garbage_measured else {}

    st.markdown("<hr class='fg-rule'>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.5, 1], gap="medium")
    with c1:
        with st.container(border=True):
            st.markdown(section_title("Objects in view over time", "How many of each object the detector sees in each analysed frame"),
                        unsafe_allow_html=True)
            if counts_fig is not None:
                st.plotly_chart(counts_fig, use_container_width=True, config=_CHART_CONFIG)
            else:
                st.caption("No objects tracked.")
    with c2:
        with st.container(border=True):
            st.markdown(section_title("Garbage by waste stream", "Share of garbage area"), unsafe_allow_html=True)
            if shares:
                st.plotly_chart(_waste_chart(shares), use_container_width=True, config=_CHART_CONFIG)
            else:
                st.caption("Not measured for this video." if not garbage_measured else "No garbage measured.")
    if cov_fig is not None and garbage_measured:
        with st.container(border=True):
            st.markdown(section_title("Garbage coverage over time", "Share of the frame covered by garbage masks"), unsafe_allow_html=True)
            st.plotly_chart(cov_fig, use_container_width=True, config=_CHART_CONFIG)

    tracked = objects.get("objects") or []
    if tracked:
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
