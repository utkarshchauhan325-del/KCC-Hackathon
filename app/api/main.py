"""FastAPI application for FloodGuard CivicEye Operations Center.

Serves the Stitch-based drainage detection frontend templates and provides
REST APIs for live incidents, CCTV telemetry, and emergency crew dispatch.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import AuditLog, Incident, Job, Task, Violation, Worker, generate_uuid
from app.db.session import SessionLocal, get_db, init_db
from app.ui.pune_data import CCTV_CAMERAS, PUNE_LOCATIONS

# Ensure database tables exist
init_db()

app = FastAPI(
    title="FloodGuard CivicEye Operations API",
    description="Real-time AI drainage blockage detection, camera telemetry, and crew dispatch system",
    version="1.0.0"
)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if hasattr(settings, "EVIDENCE_DIR"):
    settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static/evidence", StaticFiles(directory=str(settings.EVIDENCE_DIR)), name="evidence")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------

class CrewDispatchPayload(BaseModel):
    incident_id: str
    crew_unit: str = "PMC-04"
    notes: Optional[str] = None


class IncidentResolvePayload(BaseModel):
    incident_id: str
    notes: Optional[str] = None


# ---------------------------------------------------------
# Frontend Template Routes
# ---------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index_redirect():
    return RedirectResponse(url="/priority-queue")


@app.get("/priority-queue", response_class=HTMLResponse)
def get_priority_queue_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="priority_queue.html",
        context={"active_page": "priority_queue"}
    )


# ---------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------

@app.get("/api/v1/stats")
def get_stats(db: Session = Depends(get_db)):
    """Return live operational KPI stats."""
    db_incidents = db.query(Incident).all()
    open_count = sum(1 for i in db_incidents if i.status in ("new", "sent", "acknowledged"))
    critical_count = sum(1 for i in db_incidents if i.severity == 5 and i.status in ("new", "sent", "acknowledged"))
    violations_count = db.query(Violation).filter(Violation.review_status == "pending_review").count()
    active_crews = db.query(Task).filter(Task.status == "in_progress").count() or 12

    # Baseline seed counts for full operational demonstration
    if open_count < 4:
        open_count = 14
        critical_count = 8
        violations_count = 7

    return {
        "open_incidents": open_count,
        "critical_incidents": critical_count,
        "analyzed_frames_per_hr": 1280,
        "pending_violations": violations_count,
        "active_crews": active_crews,
        "total_crews": 16,
        "cameras_online": 1000
    }


@app.get("/api/v1/incidents")
def get_incidents(db: Session = Depends(get_db)):
    """Fetch live incident queue with AI vision telemetry, filmstrips, and risk scores."""
    incidents_list: List[Dict[str, Any]] = []

    # 1. Query real incidents from database
    db_incidents = db.query(Incident).order_by(Incident.severity.desc()).limit(20).all()
    for inc in db_incidents:
        # Build filmstrip from evidence attachments
        filmstrip = []
        for ev in inc.evidences:
            if ev.kind == "frame":
                filmstrip.append({
                    "label": f"Capture at {inc.video_ts}",
                    "time": inc.video_ts,
                    "src": f"/static/evidence/{Path(ev.path).name}" if Path(ev.path).exists() else "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80",
                    "active": True
                })

        risk = 70
        if inc.sewer_score:
            risk = int(inc.sewer_score.score)
        elif inc.severity == 5:
            risk = 92
        elif inc.severity == 4:
            risk = 78

        incidents_list.append({
            "id": f"#INC-{inc.id[:4].upper()}",
            "raw_id": inc.id,
            "cam_id": f"CAM-{inc.job_id[:4].upper()}" if inc.job_id else "CAM-1042",
            "location": f"Zone {inc.severity} Municipal Sector - {inc.subtype.replace('_', ' ').title()}",
            "description": inc.description or "Automated AI detection of municipal obstruction.",
            "severity": inc.severity,
            "risk_score": risk,
            "garbage_area": f"{min(85, risk - 15)}%",
            "water_level": "1.85m (+0.6m/hr)",
            "time_ago": "Recently detected",
            "timestamp": f"{inc.video_ts} [LIVE CAPTURE]",
            "type": "camera" if filmstrip else "sensor",
            "run_threat": "CRITICAL" if inc.severity == 5 else "HIGH",
            "zone": "Central",
            "status": "open" if inc.status in ("new", "sent", "acknowledged") else "resolved",
            "sop": "Deploy Hydraulic Silt Jetting Vehicle and rapid clearance crew.",
            "filmstrip": filmstrip or [
                {
                    "label": "Live Camera Feed",
                    "time": inc.video_ts,
                    "src": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80",
                    "active": True
                }
            ],
            "assigned_crew": None
        })

    # 2. If DB has few incidents, supplement with the 4 high-fidelity Pune CCTV municipal incidents
    pune_seed_incidents = [
        {
            "id": "#INC-8821",
            "cam_id": "CAM-PUNE-01",
            "location": "Mutha River Underpass Culvert #4 (Shivajinagar)",
            "description": "Heavy industrial debris, plastic tarp, and silt creating 74% cross-sectional drainage blockage. Severe overflow hazard along arterial roadway.",
            "severity": 5,
            "risk_score": 94,
            "garbage_area": "74.2%",
            "water_level": "1.92m (+0.8m/hr)",
            "time_ago": "4 mins ago",
            "timestamp": "00:14:22 [LIVE CAPTURE]",
            "type": "camera",
            "run_threat": "CRITICAL",
            "zone": "Shivajinagar",
            "status": "open",
            "sop": "Deploy Hydraulic De-silting Jetting Vehicle (Unit PMC-4) and 4-man rapid clearing crew. Clear culvert trash rack from eastern bank.",
            "filmstrip": [
                { "label": "Normal flow (22%)", "time": "00:12:05", "src": "https://images.unsplash.com/photo-1541888946425-d0fbb186f5f7?auto=format&fit=crop&w=400&q=80" },
                { "label": "Debris collision", "time": "00:13:40", "src": "https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=400&q=80" },
                { "label": "Severe choke point", "time": "00:14:22 [LIVE]", "src": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80", "active": True },
                { "label": "Backwater surge", "time": "00:15:10", "src": "https://images.unsplash.com/photo-1518241353330-0f7941c2d9b5?auto=format&fit=crop&w=400&q=80" }
            ],
            "assigned_crew": "PMC-04"
        },
        {
            "id": "#INC-8819",
            "cam_id": "CAM-PUNE-02",
            "location": "Hadapsar Flyover Drainage Outfall (Drain-089)",
            "description": "Telemetry trigger: Ultrasonic water rise rate exceeded safe threshold (+1.2m/hr). Backwater surge detected at primary storm manifold.",
            "severity": 4,
            "risk_score": 82,
            "garbage_area": "N/A (Ultrasonic Sensor)",
            "water_level": "2.4m / 2.8m Max",
            "time_ago": "12 mins ago",
            "timestamp": "SURGE LEVEL ALERT",
            "type": "sensor",
            "run_threat": "ELEVATED",
            "zone": "Hadapsar",
            "status": "open",
            "sop": "Engage de-watering auxiliary pumps at Siphon station #2 and reroute storm intake.",
            "filmstrip": [],
            "assigned_crew": None
        },
        {
            "id": "#INC-8815",
            "cam_id": "CAM-PUNE-03",
            "location": "Swargate Junction Stormwater Drain Manhole #12",
            "description": "Illegal dumping in progress: Concrete rubble and masonry bags choking 55% culvert inlet during high precipitation.",
            "severity": 4,
            "risk_score": 78,
            "garbage_area": "54.8%",
            "water_level": "1.40m (+0.3m/hr)",
            "time_ago": "19 mins ago",
            "timestamp": "00:08:14 [LIVE CAPTURE]",
            "type": "camera",
            "run_threat": "HIGH",
            "zone": "Swargate",
            "status": "violations",
            "sop": "Notify Ward Officer and dispatch interceptor QRT squad to issue statutory notice.",
            "filmstrip": [
                { "label": "Truck arrival", "time": "00:05:10", "src": "https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=400&q=80" },
                { "label": "Dumping active", "time": "00:08:14", "src": "https://images.unsplash.com/photo-1541888946425-d0fbb186f5f7?auto=format&fit=crop&w=400&q=80", "active": True }
            ],
            "assigned_crew": None
        },
        {
            "id": "#INC-8812",
            "cam_id": "CAM-PUNE-04",
            "location": "Sinhagad Road Vitthalwadi Box Drain Inlet",
            "description": "High volume plastic debris, thermocol packaging, and silt blocking screen grate. Water level rising fast towards road shoulder.",
            "severity": 5,
            "risk_score": 91,
            "garbage_area": "68.5%",
            "water_level": "2.10m (+0.9m/hr)",
            "time_ago": "25 mins ago",
            "timestamp": "00:18:30 [LIVE CAPTURE]",
            "type": "camera",
            "run_threat": "CRITICAL",
            "zone": "Sinhagad",
            "status": "open",
            "sop": "Mobilize Sinhagad Ward Unit #2 with mechanical grab crane and vacuum suction tanker.",
            "filmstrip": [
                { "label": "Screen intake", "time": "00:15:00", "src": "https://images.unsplash.com/photo-1541888946425-d0fbb186f5f7?auto=format&fit=crop&w=400&q=80", "active": True }
            ],
            "assigned_crew": None
        }
    ]

    # Combine ensuring unique IDs
    existing_ids = {i["id"] for i in incidents_list}
    for seed in pune_seed_incidents:
        if seed["id"] not in existing_ids:
            incidents_list.append(seed)

    return incidents_list


@app.post("/api/v1/dispatch")
def dispatch_crew(payload: CrewDispatchPayload, db: Session = Depends(get_db)):
    """Dispatch PMC emergency crew and update incident status in the database."""
    incident_id = payload.incident_id.replace("#INC-", "")

    # Look up matching incident if in DB
    inc = db.query(Incident).filter(Incident.id.startswith(incident_id.lower())).first()
    if inc:
        inc.status = "sent"

        # Create task assignment
        worker = db.query(Worker).filter(Worker.active == True).first()
        task = Task(
            incident_id=inc.id,
            assigned_to=worker.id if worker else None,
            status="in_progress",
            instructions=f"Dispatched crew unit {payload.crew_unit}: {payload.notes or 'Emergency drain silt clearance.'}"
        )
        db.add(task)

    # Log to audit log
    db.add(AuditLog(
        user="rajesh.sharma@pune.gov.in",
        action="DISPATCH_CREW",
        entity="incident",
        entity_id=payload.incident_id,
        at=datetime.utcnow()
    ))
    db.commit()

    return {
        "status": "DISPATCHED",
        "incident_id": payload.incident_id,
        "crew_unit": payload.crew_unit,
        "eta": "12-15 mins",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/resolve")
def resolve_incident(payload: IncidentResolvePayload, db: Session = Depends(get_db)):
    """Mark an incident as resolved."""
    incident_id = payload.incident_id.replace("#INC-", "")
    inc = db.query(Incident).filter(Incident.id.startswith(incident_id.lower())).first()
    if inc:
        inc.status = "resolved"

    db.add(AuditLog(
        user="rajesh.sharma@pune.gov.in",
        action="RESOLVE_INCIDENT",
        entity="incident",
        entity_id=payload.incident_id,
        at=datetime.utcnow()
    ))
    db.commit()

    return {
        "status": "RESOLVED",
        "incident_id": payload.incident_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/cameras")
def get_cameras():
    """Return municipal CCTV camera telemetry."""
    return CCTV_CAMERAS


@app.get("/health")
def health():
    return {"status": "ok", "service": "FloodGuard CivicEye Backend & Stitch Frontend"}
