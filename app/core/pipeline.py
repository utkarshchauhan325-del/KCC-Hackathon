"""End-to-end processing pipeline for CivicEye."""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

from app.config import settings
from app.db.session import SessionLocal
from app.db.models import Job, Incident, Evidence, SewerScore, Violation
from app.core.gemini_client import GeminiVideoClient
from app.core.evidence import (
    extract_frame_at_timestamp,
    scale_bbox_to_pixels,
    select_keyframes,
    encode_jpeg,
    annotate_frame,
    crop_bbox,
    blur_bystander_faces,
    save_image,
    timestamp_to_seconds,
    generate_annotated_surveillance_video,
)
from app.core.dedupe import deduplicate_infra_issues
from app.core.plates import is_valid_indian_plate
from app.notify.alerts import send_incident_alert
from app.core.scoring import compute_sewer_score, compute_observed_hazard_scores
from app.core.detector import CivicObjectDetector, GarbageExemplar

logger = logging.getLogger("civiceye.pipeline")

class CivicEyePipeline:
    """Orchestrates end-to-end video analysis, evidence extraction, scoring, and DB persistence."""

    def __init__(self, client: Optional[GeminiVideoClient] = None, detector: Optional[CivicObjectDetector] = None):
        self.client = client or GeminiVideoClient()
        self.detector = detector

    def _get_detector(self) -> Optional[CivicObjectDetector]:
        if self.detector is None and settings.DETECTOR_ENABLED:
            self.detector = CivicObjectDetector()
        return self.detector

    def _teach_garbage(self, detector: CivicObjectDetector, video_path: Path, issues: list, log_progress) -> None:
        """Have Gemini box garbage on a few frames; the detector uses them as visual prompts.

        Without examples the detector falls back to its text prompts, which miss most
        real-world garbage, so a failure here is reported but not fatal.
        """
        frames = select_keyframes(video_path, issues, settings.DETECTOR_EXEMPLAR_FRAMES)
        if not frames:
            return
        log_progress(f"[Garbage Prompts] Asking LLM model to mark garbage on {len(frames)} frames to teach the local detector...")
        try:
            resp = self.client.locate_garbage([encode_jpeg(f, max_side=1024) for _, f in frames])
        except Exception as e:
            logger.warning(f"Garbage exemplar request failed: {e}")
            log_progress(f"[Notice] Could not get garbage examples from LLM model ({e}); detector will use text prompts only.")
            detector.set_exemplars([])
            return

        exemplars = []
        for marked in resp.frames:
            if not 1 <= marked.image_index <= len(frames) or not marked.regions:
                continue
            frame = frames[marked.image_index - 1][1]
            h, w = frame.shape[:2]
            boxes = [scale_bbox_to_pixels(r.box, w, h) for r in marked.regions]
            valid = [(b, r.waste_type) for b, r in zip(boxes, marked.regions) if b[2] - b[0] >= 8 and b[3] - b[1] >= 8]
            if valid:
                exemplars.append(GarbageExemplar(frame, [b for b, _ in valid], [t for _, t in valid]))
            detector.set_exemplars(exemplars)
        regions = sum(len(e.boxes) for e in exemplars)
        log_progress(f"LLM model marked {regions} garbage region(s) on {len(exemplars)} frame(s).")

    def process_video(
        self,
        video_path: Path,
        source_gps: Optional[str] = None,
        run_pass_b: bool = True,
        job_id: Optional[str] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Execute full inspection on video file with graceful degradation."""
        video_path = Path(video_path)
        if not video_path.is_file():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        def log_progress(msg: str):
            logger.info(msg)
            if progress_cb:
                progress_cb(msg)

        db = SessionLocal()
        # Initialize or retrieve Job
        if job_id:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                job = Job(id=job_id, filename=video_path.name, source_gps=source_gps, status="processing")
                db.add(job)
        else:
            job = Job(filename=video_path.name, source_gps=source_gps, status="processing")
            db.add(job)
        db.commit()
        db.refresh(job)

        uploaded_file = None
        evidence_dir = settings.EVIDENCE_DIR / job.id
        evidence_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Upload video to Gemini Files API
            # Upload and Pass A failures are fatal: reporting "no hazards" for a video
            # that was never analysed would look like an all-clear to the municipality.
            log_progress(f"[Upload] Uploading {video_path.name} to LLM model Files API...")
            uploaded_file = self.client.upload_video(video_path)
            log_progress("[Ready] Video ready for multimodal inspection.")

            # 2. Pass A: Infrastructure issues
            log_progress("[Pass A] Scanning infrastructure hazards (drains, garbage, road)...")
            infra_resp = self.client.analyze_infrastructure(uploaded_file)
            raw_issues = infra_resp.issues
            log_progress(f"Found {len(raw_issues)} hazard sightings.")

            # 3. Deduplicate issues
            deduped_issues = deduplicate_infra_issues(raw_issues)
            log_progress(f"Deduplicated to {len(deduped_issues)} unique civic issues.")

            created_incidents: List[Incident] = []
            sewer_assessments = []

            # 4. Process each infrastructure incident
            for issue in deduped_issues:
                incident = Incident(
                    job_id=job.id,
                    type=issue.category,
                    subtype=issue.subtype,
                    severity=issue.severity,
                    video_ts=issue.best_frame_ts,
                    description=issue.description,
                    confidence=issue.confidence,
                    location_source="fixed_cctv" if source_gps else "manual_input",
                    status="new",
                )
                if source_gps and "," in source_gps:
                    try:
                        parts = source_gps.split(",")
                        incident.lat = float(parts[0].strip())
                        incident.lng = float(parts[1].strip())
                    except Exception:
                        pass

                db.add(incident)
                db.commit()
                db.refresh(incident)
                created_incidents.append(incident)

                # Extract still frame
                ts_sec = timestamp_to_seconds(issue.best_frame_ts)
                frame = extract_frame_at_timestamp(video_path, ts_sec)

                if frame is not None:
                    # Save raw frame
                    raw_frame_path = evidence_dir / f"incident_{incident.id}_raw.jpg"
                    save_image(frame, raw_frame_path)
                    db.add(Evidence(incident_id=incident.id, kind="frame", path=str(raw_frame_path)))

                    # Save annotated frame
                    annotated = annotate_frame(frame, issue.box, label=issue.subtype, severity=issue.severity)
                    annotated_path = evidence_dir / f"incident_{incident.id}_annotated.jpg"
                    save_image(annotated, annotated_path)
                    db.add(Evidence(incident_id=incident.id, kind="annotated", path=str(annotated_path)))

                # 5. Pass C: Sewer assessment if drainage issue
                if issue.category == "drainage":
                    log_progress(f"[Pass C] Computing Sewer Overflow Risk Score for '{issue.subtype}' at {issue.best_frame_ts}...")
                    try:
                        time.sleep(1.0)
                        sewer_resp = self.client.assess_sewer_point(uploaded_file, issue.best_frame_ts)
                        score, band, breakdown = compute_sewer_score(sewer_resp)

                        sewer_score_row = SewerScore(
                            incident_id=incident.id,
                            score=score,
                            band=band,
                            breakdown_json=json.dumps(breakdown),
                            raw_assessment_json=json.dumps(sewer_resp.model_dump()),
                        )
                        db.add(sewer_score_row)
                        sewer_assessments.append(sewer_resp)
                        log_progress(f"Sewer Risk Score: {score}/100 [{band.upper()}]")
                    except Exception as e:
                        logger.warning(f"Pass C sewer assessment skipped: {e}")
                        log_progress(f"[Notice] Pass C sewer assessment skipped: {e}")

            # 6. Pass B: Violator Detection (if requested)
            dumping_events = 0
            if run_pass_b:
                log_progress("[Pass B] Scanning for illegal waste dumping violators...")
                try:
                    time.sleep(1.0)
                    violator_resp = self.client.analyze_violators(uploaded_file)
                    for event in violator_resp.events:
                        violator_inc = Incident(
                            job_id=job.id,
                            type="garbage",
                            subtype="dumping_violation",
                            severity=4,
                            video_ts=event.best_frame_ts,
                            description=event.description,
                            confidence=event.confidence,
                            location_source="fixed_cctv" if source_gps else "manual_input",
                            status="pending_review",
                        )
                        db.add(violator_inc)
                        db.commit()
                        db.refresh(violator_inc)

                        ts_sec = timestamp_to_seconds(event.best_frame_ts)
                        frame = extract_frame_at_timestamp(video_path, ts_sec)

                        if frame is not None:
                            privacy_frame = blur_bystander_faces(frame, primary_box=event.person_box)
                            priv_path = evidence_dir / f"violation_{violator_inc.id}_frame.jpg"
                            save_image(privacy_frame, priv_path)
                            db.add(Evidence(incident_id=violator_inc.id, kind="frame", path=str(priv_path)))

                            for kind, box in (
                                ("crop_person", event.person_box),
                                ("crop_vehicle", event.vehicle_box),
                                ("crop_plate", event.plate_box),
                            ):
                                if box is None:
                                    continue
                                crop = crop_bbox(frame, box)
                                if crop.size == 0:
                                    continue
                                crop_path = evidence_dir / f"violation_{violator_inc.id}_{kind}.jpg"
                                save_image(crop, crop_path)
                                db.add(Evidence(incident_id=violator_inc.id, kind=kind, path=str(crop_path)))

                        violation_record = Violation(
                            incident_id=violator_inc.id,
                            plate_text=event.plate_text,
                            plate_valid=is_valid_indian_plate(event.plate_text),
                            plate_legibility=event.plate_legibility,
                            vehicle_type=event.vehicle_type,
                            review_status="pending_review",
                        )
                        db.add(violation_record)
                        dumping_events += 1
                    log_progress(f"Pass B completed: {len(violator_resp.events)} violator events queued.")
                except Exception as e:
                    logger.warning(f"Pass B violator detection skipped: {e}", exc_info=True)
                    log_progress(f"[Pass B Warning] Violator detection failed: {e}")

            # 7. Per-frame object segmentation + tracking, rendered into the evidence video
            annotated_video_path = evidence_dir / f"surveillance_{job.id}_annotated.mp4"
            render_kwargs = dict(
                video_path=video_path,
                output_path=annotated_video_path,
                vlm_issues=deduped_issues,
                camera_meta={"gps": source_gps or "not set", "name": "Pune Surveillance Feed"},
            )
            detector = self._get_detector()
            object_summary = None
            if detector:
                self._teach_garbage(detector, video_path, deduped_issues, log_progress)
                log_progress("[Local YOLOE] Segmenting and tracking objects frame by frame...")
                try:
                    _, object_summary = generate_annotated_surveillance_video(
                        **render_kwargs, detector=detector, progress_cb=log_progress
                    )
                except Exception as e:
                    logger.warning(f"Local detector failed: {e}", exc_info=True)
                    log_progress(f"[Notice] Local detector failed ({e}); video shows LLM model findings only.")
                    detector = None
            if not detector:
                log_progress("[Evidence] Rendering evidence video with LLM model findings...")
                generate_annotated_surveillance_video(**render_kwargs)
            if object_summary:
                log_progress(
                    f"Tracked {len(object_summary['objects'])} objects: "
                    + ", ".join(f"{n} {c}" for c, n in object_summary["counts_by_category"].items())
                )

            # 8. Deterministic scores from observed evidence only (Pass C + detector + Pass B)
            garbage_severities = [i.severity for i in deduped_issues if i.category == "garbage"]
            scores = compute_observed_hazard_scores(
                sewer_assessments=sewer_assessments,
                dumping_detected=dumping_events > 0,
                garbage_coverage=object_summary["garbage_coverage"] if object_summary else None,
                vlm_garbage_severity=max(garbage_severities) if garbage_severities else None,
            )

            # Save annotated video evidence (Evidence rows require an incident)
            if created_incidents:
                db.add(Evidence(
                    incident_id=created_incidents[0].id,
                    kind="annotated_video",
                    path=str(annotated_video_path),
                ))

            job.status = "completed"
            db.commit()

            # Hazards go to the municipality immediately; dumping violations wait for
            # officer approval in the Priority Queue before any evidence is sent.
            alertable = [i for i in created_incidents if i.severity >= settings.ALERT_MIN_SEVERITY]
            if alertable:
                log_progress(f"[Alert] Alerting municipal corporation about {len(alertable)} hazard(s)...")
                for incident in alertable:
                    logs = send_incident_alert(db, incident)
                    sent = sum(1 for log in logs if log.status == "sent")
                    if not logs:
                        log_progress("[Notice] No alert channel configured (SMTP / Telegram / webhook); alert not sent.")
                        break
                    log_progress(f"Alert for '{incident.subtype}': {sent}/{len(logs)} channel(s) delivered.")
            log_progress("[Complete] Analysis complete.")

            result = {
                "job_id": job.id,
                "status": "completed",
                "filename": video_path.name,
                "incidents_count": len(created_incidents),
                "violations_count": dumping_events,
                "annotated_video_path": str(annotated_video_path),
                "objects": object_summary,
                **scores,
            }
            (evidence_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            return result

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            db.commit()
            logger.error(f"Pipeline error for job {job.id}: {e}", exc_info=True)
            raise e
        finally:
            if uploaded_file:
                self.client.delete_file(uploaded_file.name)
            db.close()
