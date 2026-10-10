"""SQLAlchemy database models for CivicEye."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    status = Column(String(50), default="processing")  # processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    source_gps = Column(String(100), nullable=True)     # "lat,lng" or null
    error = Column(Text, nullable=True)

    incidents = relationship("Incident", back_populates="job", cascade="all, delete-orphan")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    type = Column(String(50), nullable=False)           # garbage, drainage, road, other
    subtype = Column(String(100), nullable=False)
    severity = Column(Integer, default=1)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    location_source = Column(String(50), default="manual_input") # fixed_cctv, manual_input, srt_gps, vlm_inferred
    video_ts = Column(String(20), nullable=False)       # "MM:SS"
    description = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    status = Column(String(50), default="new")           # new, sent, acknowledged, resolved, rejected
    dedupe_key = Column(String(100), nullable=True, index=True)

    job = relationship("Job", back_populates="incidents")
    evidences = relationship("Evidence", back_populates="incident", cascade="all, delete-orphan")
    violation = relationship("Violation", back_populates="incident", uselist=False, cascade="all, delete-orphan")
    sewer_score = relationship("SewerScore", back_populates="incident", uselist=False, cascade="all, delete-orphan")
    alerts = relationship("AlertLog", back_populates="incident", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="incident", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidences"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    kind = Column(String(50), nullable=False) # frame, annotated, crop_person, crop_vehicle, crop_plate, clip
    path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="evidences")

class Violation(Base):
    __tablename__ = "violations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    plate_text = Column(String(50), nullable=True)
    plate_valid = Column(Boolean, default=False)
    plate_legibility = Column(String(50), default="none")
    vehicle_type = Column(String(100), nullable=True)
    review_status = Column(String(50), default="pending_review") # pending_review, approved, rejected
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    incident = relationship("Incident", back_populates="violation")

class SewerScore(Base):
    __tablename__ = "sewer_scores"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    score = Column(Float, nullable=False)
    band = Column(String(50), nullable=False) # Low, Watch, High, Critical
    breakdown_json = Column(Text, nullable=False)
    raw_assessment_json = Column(Text, nullable=False)

    incident = relationship("Incident", back_populates="sewer_score")

class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    channel = Column(String(50), nullable=False) # email, telegram, webhook
    recipient = Column(String(255), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="sent")  # sent, failed, throttled
    response = Column(Text, nullable=True)

    incident = relationship("Incident", back_populates="alerts")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user = Column(String(100), default="system")
    action = Column(String(100), nullable=False) # e.g. "approved_violation", "rejected_incident"
    entity = Column(String(50), nullable=False)  # incident, violation, etc.
    entity_id = Column(String(36), nullable=True)
    at = Column(DateTime, default=datetime.utcnow)

class Worker(Base):
    __tablename__ = "workers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    ward = Column(String(50), nullable=True)
    zone = Column(String(50), nullable=True)
    skills = Column(String(255), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def is_active(self) -> bool:
        return bool(self.active)

    @is_active.setter
    def is_active(self, val: bool) -> None:
        self.active = val

    tasks = relationship("Task", back_populates="worker", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    worker_id = Column(String(36), ForeignKey("workers.id"), nullable=False)
    assigned_by = Column(String(100), default="Duty Officer")
    assigned_at = Column(DateTime, default=datetime.utcnow)
    due_at = Column(DateTime, nullable=True)
    priority = Column(String(20), default="high")  # critical, high, medium, low
    instructions = Column(Text, nullable=True)
    status = Column(String(50), default="assigned")  # assigned, in_progress, submitted, verified, rejected, manual_review

    incident = relationship("Incident", back_populates="tasks")
    worker = relationship("Worker", back_populates="tasks")
    submissions = relationship("TaskSubmission", back_populates="task", cascade="all, delete-orphan", order_by="TaskSubmission.attempt_number")

class TaskSubmission(Base):
    __tablename__ = "task_submissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    attempt_number = Column(Integer, default=1)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    after_photo_path = Column(String(500), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    verification_status = Column(String(50), default="pending")  # verified, rejected, manual_review
    quality_score = Column(Float, nullable=True)
    gemini_cleaned = Column(Boolean, nullable=True)
    gemini_confidence = Column(Float, nullable=True)
    gemini_reason = Column(Text, nullable=True)
    yoloe_garbage_before_pct = Column(Float, nullable=True)
    yoloe_garbage_after_pct = Column(Float, nullable=True)
    rejection_reasons = Column(Text, nullable=True)  # JSON-serialized list of issues
    worker_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    task = relationship("Task", back_populates="submissions")


import secrets
import hashlib

def hash_password(password: str) -> str:
    """Hash a password securely using salted SHA-256."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain password against the stored salt:hash string."""
    if not password_hash or ":" not in password_hash:
        return False
    salt, hashed = password_hash.split(":", 1)
    test_hash = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return secrets.compare_digest(hashed, test_hash)

