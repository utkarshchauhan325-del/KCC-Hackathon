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
    annotate_frame,
    crop_bbox,
    blur_bystander_faces,
    save_image,
    timestamp_to_seconds,
)
from app.core.dedupe import deduplicate_infra_issues
from app.core.scoring import compute_sewer_score

logger = logging.getLogger("civiceye.pipeline")

class CivicEyePipeline:
    """Orchestrates end-to-end video analysis, evidence extraction, scoring, and DB persistence."""

    def __init__(self, client: Optional[GeminiVideoClient] = None):
        self.client = client or GeminiVideoClient()

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
            log_progress(f"📤 Uploading {video_path.name} to Gemini Files API...")
            uploaded_file = self.client.upload_video(video_path)
            log_progress(f"✅ Video ready for multimodal inspection.")

            # 2. Pass A: Infrastructure issues
            log_progress("🔍 Scanning infrastructure hazards (Pass A: drains, garbage, road)...")
            infra_resp = self.client.analyze_infrastructure(uploaded_file)
            raw_issues = infra_resp.issues
            log_progress(f"Found {len(raw_issues)} hazard sightings.")

            # 3. Deduplicate issues
            deduped_issues = deduplicate_infra_issues(raw_issues)
            log_progress(f"Deduplicated to {len(deduped_issues)} unique civic issues.")

            created_incidents: List[Incident] = []

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
                    log_progress(f"🌊 Computing Sewer Overflow Risk Score for '{issue.subtype}' at {issue.best_frame_ts}...")
                    try:
                        time.sleep(2.0) # Breather to avoid 503 burst
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
                        log_progress(f"Sewer Risk Score: {score}/100 [{band.upper()}]")
                    except Exception as e:
                        logger.warning(f"Pass C sewer assessment failed (non-fatal): {e}")

            # 6. Pass B: Violator Detection (if requested)
            if run_pass_b:
                log_progress("👥 Scanning for illegal waste dumping violators (Pass B)...")
                try:
                    time.sleep(2.0) # Breather
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
                            status="pending_review", # Strictly pending review
                        )
                        db.add(violator_inc)
                        db.commit()
                        db.refresh(violator_inc)

                        # Extract frame & apply bystander blurring
                        ts_sec = timestamp_to_seconds(event.best_frame_ts)
                        frame = extract_frame_at_timestamp(video_path, ts_sec)

                        if frame is not None:
                            # Privacy safeguard: blur bystander faces
                            privacy_frame = blur_bystander_faces(frame, primary_box=event.person_box)
                            priv_path = evidence_dir / f"violation_{violator_inc.id}_frame.jpg"
                            save_image(privacy_frame, priv_path)
                            db.add(Evidence(incident_id=violator_inc.id, kind="frame", path=str(priv_path)))

                            # Person crop
                            if event.person_box:
                                p_crop = crop_bbox(frame, event.person_box)
                                p_path = evidence_dir / f"violation_{violator_inc.id}_crop_person.jpg"
                                save_image(p_crop, p_path)
                                db.add(Evidence(incident_id=violator_inc.id, kind="crop_person", path=str(p_path)))

                            # Vehicle crop
                            if event.vehicle_box:
                                v_crop = crop_bbox(frame, event.vehicle_box)
                                v_path = evidence_dir / f"violation_{violator_inc.id}_crop_vehicle.jpg"
                                save_image(v_crop, v_path)
                                db.add(Evidence(incident_id=violator_inc.id, kind="crop_vehicle", path=str(v_path)))

                            # Plate crop
                            if event.plate_box:
                                pl_crop = crop_bbox(frame, event.plate_box)
                                pl_path = evidence_dir / f"violation_{violator_inc.id}_crop_plate.jpg"
                                save_image(pl_crop, pl_path)
                                db.add(Evidence(incident_id=violator_inc.id, kind="crop_plate", path=str(pl_path)))

                        violation_record = Violation(
                            incident_id=violator_inc.id,
                            plate_text=event.plate_text,
                            plate_legibility=event.plate_legibility,
                            vehicle_type=event.vehicle_type,
                            review_status="pending_review",
                        )
                        db.add(violation_record)
                    log_progress(f"Pass B completed: {len(violator_resp.events)} violator events queued.")
                except Exception as e:
                    logger.warning(f"Pass B violator detection failed (non-fatal): {e}")
                    log_progress("⚠️ Violator pass skipped due to API rate limit.")

            job.status = "completed"
            db.commit()
            log_progress("🎉 All processing complete! Incident records generated.")

            return {
                "job_id": job.id,
                "status": "completed",
                "incidents_count": len(created_incidents),
            }

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
