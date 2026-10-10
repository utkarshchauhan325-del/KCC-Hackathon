"""Municipal alert dispatch over email, Telegram and webhook, logged to AlertLog."""

import base64
import logging
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List, Any

import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Incident, AlertLog

logger = logging.getLogger("civiceye.notify")

# Evidence attached to each alert, in send order
HAZARD_EVIDENCE_KINDS = ["annotated", "frame"]
VIOLATION_EVIDENCE_KINDS = ["frame", "crop_person", "crop_vehicle", "crop_plate"]


def _evidence_paths(incident: Incident) -> List[Path]:
    is_violation = incident.violation is not None
    kinds = VIOLATION_EVIDENCE_KINDS if is_violation else HAZARD_EVIDENCE_KINDS
    by_kind = {ev.kind: Path(ev.path) for ev in incident.evidences}
    paths = [by_kind[k] for k in kinds if k in by_kind and by_kind[k].is_file()]
    # Hazards only need the clearest still: annotated if available, otherwise raw
    return paths if is_violation else paths[:1]


def build_alert(incident: Incident) -> Dict[str, Any]:
    """Assemble subject, plain-text body, JSON payload and image attachments for an incident."""
    violation = incident.violation
    location = "Location not provided"
    maps_url = None
    if incident.lat is not None and incident.lng is not None:
        location = f"{incident.lat:.6f}, {incident.lng:.6f}"
        maps_url = f"https://maps.google.com/?q={incident.lat},{incident.lng}"

    if violation:
        subject = f"[CivicEye] Illegal dumping violation - {violation.vehicle_type or 'pedestrian'}"
    else:
        label = incident.subtype.replace("_", " ")
        subject = f"[CivicEye] {incident.type.title()} hazard: {label} (severity {incident.severity}/5)"

    lines = [
        subject.replace("[CivicEye] ", ""),
        "",
        f"Description: {incident.description}",
        f"Category: {incident.type} / {incident.subtype}",
        f"Severity: {incident.severity}/5",
        f"AI confidence: {incident.confidence:.0%}",
        f"Video timestamp: {incident.video_ts}",
        f"Source video: {incident.job.filename if incident.job else 'unknown'}",
        f"Location: {location}",
    ]
    if maps_url:
        lines.append(f"Map: {maps_url}")
    if violation:
        lines += [
            "",
            f"Vehicle type: {violation.vehicle_type or 'none / on foot'}",
            f"Number plate: {violation.plate_text or 'not legible'} "
            f"(legibility: {violation.plate_legibility}, format valid: {'yes' if violation.plate_valid else 'no'})",
            f"Reviewed and approved by: {violation.reviewed_by or 'unknown'}",
            f"Approved at: {violation.reviewed_at:%Y-%m-%d %H:%M} UTC" if violation.reviewed_at else "",
        ]
    lines += ["", f"Incident ID: {incident.id}"]
    body = "\n".join(line for line in lines if line is not None)

    payload = {
        "incident_id": incident.id,
        "kind": "violation" if violation else "hazard",
        "category": incident.type,
        "subtype": incident.subtype,
        "severity": incident.severity,
        "confidence": incident.confidence,
        "description": incident.description,
        "video_ts": incident.video_ts,
        "lat": incident.lat,
        "lng": incident.lng,
    }
    if violation:
        payload.update({
            "vehicle_type": violation.vehicle_type,
            "plate_text": violation.plate_text,
            "plate_legibility": violation.plate_legibility,
            "plate_valid": violation.plate_valid,
            "reviewed_by": violation.reviewed_by,
        })

    return {"subject": subject, "body": body, "payload": payload, "attachments": _evidence_paths(incident)}


def send_email(subject: str, body: str, attachments: List[Path]) -> str:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = settings.ALERT_EMAIL_RECIPIENT
    msg.set_content(body)
    for path in attachments:
        mime, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (mime or "application/octet-stream").split("/", 1)
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)

    timeout = settings.ALERT_TIMEOUT_SECONDS
    if settings.SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout)
    else:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout)
        server.starttls()
    with server:
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.send_message(msg)
    return f"emailed {len(attachments)} attachment(s)"


def send_telegram(body: str, attachments: List[Path]) -> str:
    base = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
    timeout = settings.ALERT_TIMEOUT_SECONDS
    resp = requests.post(f"{base}/sendMessage", data={"chat_id": settings.TELEGRAM_CHAT_ID, "text": body}, timeout=timeout)
    resp.raise_for_status()
    for path in attachments:
        with open(path, "rb") as f:
            resp = requests.post(
                f"{base}/sendPhoto",
                data={"chat_id": settings.TELEGRAM_CHAT_ID, "caption": path.stem},
                files={"photo": (path.name, f)},
                timeout=timeout,
            )
        resp.raise_for_status()
    return f"message + {len(attachments)} photo(s)"


def send_webhook(payload: Dict[str, Any], attachments: List[Path]) -> str:
    body = dict(payload)
    body["evidence"] = [
        {"filename": p.name, "content_base64": base64.b64encode(p.read_bytes()).decode()}
        for p in attachments
    ]
    resp = requests.post(settings.WEBHOOK_URL, json=body, timeout=settings.ALERT_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return f"HTTP {resp.status_code}"


def configured_channels() -> List[str]:
    channels = []
    if settings.SMTP_USER and settings.SMTP_PASS and settings.ALERT_EMAIL_RECIPIENT:
        channels.append("email")
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        channels.append("telegram")
    if settings.WEBHOOK_URL:
        channels.append("webhook")
    return channels


def send_incident_alert(db: Session, incident: Incident) -> List[AlertLog]:
    """Send an incident to every configured channel and record each attempt in AlertLog.

    Returns the AlertLog rows; an empty list means no channel is configured.
    """
    channels = configured_channels()
    if not channels:
        logger.warning("No alert channel configured; incident %s not sent.", incident.id)
        return []

    alert = build_alert(incident)
    logs: List[AlertLog] = []
    for channel in channels:
        recipient = {
            "email": settings.ALERT_EMAIL_RECIPIENT,
            "telegram": settings.TELEGRAM_CHAT_ID,
            "webhook": settings.WEBHOOK_URL,
        }[channel]
        try:
            if channel == "email":
                response = send_email(alert["subject"], alert["body"], alert["attachments"])
            elif channel == "telegram":
                response = send_telegram(alert["body"], alert["attachments"])
            else:
                response = send_webhook(alert["payload"], alert["attachments"])
            status = "sent"
        except Exception as e:
            logger.warning("Alert via %s failed for incident %s: %s", channel, incident.id, e)
            response, status = str(e)[:1000], "failed"
        log = AlertLog(incident_id=incident.id, channel=channel, recipient=recipient, status=status, response=response)
        db.add(log)
        logs.append(log)

    if any(log.status == "sent" for log in logs):
        incident.status = "sent"
    db.commit()
    return logs


def send_task_assignment_alert(db: Session, task: Any) -> List[AlertLog]:
    """Notify configured channels when a task is assigned to a field worker."""
    channels = configured_channels()
    if not channels:
        return []

    incident = task.incident
    worker = task.worker
    subject = f"[FloodGuard] Task Assigned: {incident.type.title()} at {incident.subtype.replace('_', ' ')}"
    body = (
        f"Task ID: {task.id}\n"
        f"Assigned Worker: {worker.name} ({worker.phone})\n"
        f"Zone: {worker.zone or 'Central'} | Ward: {worker.ward or 'Kasba'}\n"
        f"Priority: {task.priority.upper()}\n"
        f"Due: {task.due_at or 'Immediate'}\n"
        f"Instructions: {task.instructions or 'Clean and clear site'}\n"
        f"Incident: {incident.description}\n"
    )
    attachments = _evidence_paths(incident)
    logs: List[AlertLog] = []
    for channel in channels:
        recipient = {"email": settings.ALERT_EMAIL_RECIPIENT, "telegram": settings.TELEGRAM_CHAT_ID, "webhook": settings.WEBHOOK_URL}[channel]
        try:
            if channel == "email":
                resp = send_email(subject, body, attachments)
            elif channel == "telegram":
                resp = send_telegram(body, attachments)
            else:
                resp = send_webhook({"event": "task_assigned", "task_id": task.id, "worker": worker.name}, attachments)
            status = "sent"
        except Exception as e:
            resp, status = str(e)[:1000], "failed"
        log = AlertLog(incident_id=incident.id, channel=channel, recipient=recipient, status=status, response=resp)
        db.add(log)
        logs.append(log)
    db.commit()
    return logs


def send_work_verified_alert(db: Session, task: Any, submission: Any) -> List[AlertLog]:
    """Notify when field worker submission is AI-verified and incident resolved."""
    channels = configured_channels()
    if not channels:
        return []

    incident = task.incident
    worker = task.worker
    subject = f"[FloodGuard Verified] Issue Resolved: {incident.subtype.replace('_', ' ').capitalize()}"
    body = (
        f"Site work completed and verified by AI!\n"
        f"Worker: {worker.name} ({worker.phone})\n"
        f"Task: {task.id} (Attempt {submission.attempt_number})\n"
        f"AI Confidence: {f'{submission.gemini_confidence:.0%}' if submission.gemini_confidence is not None else 'N/A'}\n"
        f"Observation: {submission.gemini_reason or 'Site cleared'}\n"
        f"Incident ID: {incident.id} marked RESOLVED.\n"
    )
    after_p = Path(submission.after_photo_path)
    attachments = [after_p] if after_p.is_file() else []
    logs: List[AlertLog] = []
    for channel in channels:
        recipient = {"email": settings.ALERT_EMAIL_RECIPIENT, "telegram": settings.TELEGRAM_CHAT_ID, "webhook": settings.WEBHOOK_URL}[channel]
        try:
            if channel == "email":
                resp = send_email(subject, body, attachments)
            elif channel == "telegram":
                resp = send_telegram(body, attachments)
            else:
                resp = send_webhook({"event": "work_verified", "task_id": task.id, "worker": worker.name}, attachments)
            status = "sent"
        except Exception as e:
            resp, status = str(e)[:1000], "failed"
        log = AlertLog(incident_id=incident.id, channel=channel, recipient=recipient, status=status, response=resp)
        db.add(log)
        logs.append(log)
    db.commit()
    return logs


def send_manual_review_alert(db: Session, task: Any, submission: Any) -> List[AlertLog]:
    """Notify admin supervisor when proof needs manual review."""
    channels = configured_channels()
    if not channels:
        return []

    incident = task.incident
    worker = task.worker
    subject = f"[FloodGuard Review Needed] Worker Proof Escalation: {incident.subtype.replace('_', ' ')}"
    body = (
        f"A task submission requires manual review by duty officer.\n"
        f"Worker: {worker.name} ({worker.phone})\n"
        f"Task ID: {task.id} (Attempt {submission.attempt_number})\n"
        f"Status: manual_review\n"
        f"AI Notes: {submission.gemini_reason or 'Borderline evaluation'}\n"
        f"Rejection/Escalation Reasons: {submission.rejection_reasons or 'None'}\n"
    )
    after_p = Path(submission.after_photo_path)
    attachments = [after_p] if after_p.is_file() else []
    logs: List[AlertLog] = []
    for channel in channels:
        recipient = {"email": settings.ALERT_EMAIL_RECIPIENT, "telegram": settings.TELEGRAM_CHAT_ID, "webhook": settings.WEBHOOK_URL}[channel]
        try:
            if channel == "email":
                resp = send_email(subject, body, attachments)
            elif channel == "telegram":
                resp = send_telegram(body, attachments)
            else:
                resp = send_webhook({"event": "manual_review", "task_id": task.id, "worker": worker.name}, attachments)
            status = "sent"
        except Exception as e:
            resp, status = str(e)[:1000], "failed"
        log = AlertLog(incident_id=incident.id, channel=channel, recipient=recipient, status=status, response=resp)
        db.add(log)
        logs.append(log)
    db.commit()
    return logs


def send_task_overdue_alert(db: Session, task: Any) -> List[AlertLog]:
    """Notify when a task has exceeded its due timestamp without completion."""
    channels = configured_channels()
    if not channels:
        return []

    incident = task.incident
    worker = task.worker
    subject = f"[FloodGuard Alert] Overdue Task: {incident.subtype.replace('_', ' ')}"
    body = (
        f"Task ID {task.id} is OVERDUE!\n"
        f"Assigned Worker: {worker.name} ({worker.phone})\n"
        f"Due At: {task.due_at}\n"
        f"Incident: {incident.description}\n"
    )
    attachments = _evidence_paths(incident)
    logs: List[AlertLog] = []
    for channel in channels:
        recipient = {"email": settings.ALERT_EMAIL_RECIPIENT, "telegram": settings.TELEGRAM_CHAT_ID, "webhook": settings.WEBHOOK_URL}[channel]
        try:
            if channel == "email":
                resp = send_email(subject, body, attachments)
            elif channel == "telegram":
                resp = send_telegram(body, attachments)
            else:
                resp = send_webhook({"event": "task_overdue", "task_id": task.id}, attachments)
            status = "sent"
        except Exception as e:
            resp, status = str(e)[:1000], "failed"
        log = AlertLog(incident_id=incident.id, channel=channel, recipient=recipient, status=status, response=resp)
        db.add(log)
        logs.append(log)
    db.commit()
    return logs

