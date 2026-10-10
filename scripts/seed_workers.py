"""Seed script for 5 demo Pune Municipal Corporation field workers with hashed passwords."""

import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db.session import SessionLocal, init_db
from app.db.models import Worker, hash_password

DEMO_WORKERS = [
    {
        "name": "Suresh Jadhav",
        "email": "suresh@pune.gov.in",
        "phone": "9820011001",
        "password": "worker123",
        "zone": "Central",
        "ward": "Kasba-Vishrambaugwada",
        "skills": "drainage, jetting, suction tanker",
    },
    {
        "name": "Ramesh Kadam",
        "email": "ramesh@pune.gov.in",
        "phone": "9820011002",
        "password": "worker123",
        "zone": "North",
        "ward": "Shivajinagar-Ghole Road",
        "skills": "solid waste, rapid clearance",
    },
    {
        "name": "Santosh Shinde",
        "email": "santosh@pune.gov.in",
        "phone": "9820011003",
        "password": "worker123",
        "zone": "South",
        "ward": "Bibwewadi",
        "skills": "dewatering, road hazard",
    },
    {
        "name": "Amit Gaikwad",
        "email": "amit@pune.gov.in",
        "phone": "9820011004",
        "password": "worker123",
        "zone": "West",
        "ward": "Kothrud-Bavdhan",
        "skills": "drainage, robotic crawler",
    },
    {
        "name": "Sachin More",
        "email": "sachin@pune.gov.in",
        "phone": "9820011005",
        "password": "worker123",
        "zone": "East",
        "ward": "Nagar Road-Vadgaon Sheri",
        "skills": "solid waste, barricading",
    },
]


def seed_workers() -> None:
    """Ensure database schema is up-to-date and seed demo field workers."""
    init_db()
    db = SessionLocal()
    try:
        created = 0
        for data in DEMO_WORKERS:
            existing = db.query(Worker).filter(
                (Worker.email == data["email"]) | (Worker.phone == data["phone"])
            ).first()
            if not existing:
                worker = Worker(
                    name=data["name"],
                    email=data["email"],
                    phone=data["phone"],
                    password_hash=hash_password(data["password"]),
                    zone=data["zone"],
                    ward=data["ward"],
                    skills=data["skills"],
                    active=True,
                )
                db.add(worker)
                created += 1
            else:
                # Update password hash if needed
                existing.name = data["name"]
                existing.zone = data["zone"]
                existing.ward = data["ward"]
                existing.skills = data["skills"]
        db.commit()
        print(f"Successfully verified/seeded {len(DEMO_WORKERS)} demo workers ({created} newly created).")
    finally:
        db.close()


if __name__ == "__main__":
    seed_workers()
