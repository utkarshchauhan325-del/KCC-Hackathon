"""Database session and engine initialization for SQLite (dev) / PostgreSQL (prod)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.db.models import Base

db_path = settings.DATA_DIR / "civiceye.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    """Create all database tables and ensure schema updates."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    # Ensure audit_logs.entity_id is nullable if table was created with NOT NULL
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            cols = conn.execute(text("PRAGMA table_info(audit_logs)")).fetchall()
            for col in cols:
                # col is (cid, name, type, notnull, dflt_value, pk)
                if col[1] == "entity_id" and col[3] == 1:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS audit_logs_new (id VARCHAR(36) PRIMARY KEY, user VARCHAR(100), action VARCHAR(100) NOT NULL, entity VARCHAR(50) NOT NULL, entity_id VARCHAR(36), at DATETIME)"))
                    conn.execute(text("INSERT INTO audit_logs_new SELECT id, user, action, entity, entity_id, at FROM audit_logs"))
                    conn.execute(text("DROP TABLE audit_logs"))
                    conn.execute(text("ALTER TABLE audit_logs_new RENAME TO audit_logs"))
                    conn.commit()
                    break
    except Exception:
        pass

    # Ensure default PMC field worker accounts are always provisioned and persisted in SQLite
    try:
        from app.db.models import Worker, hash_password
        db = SessionLocal()
        try:
            worker_count = db.query(Worker).count()
            if worker_count < 5:
                demo_workers = [
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
                for w_data in demo_workers:
                    existing = db.query(Worker).filter(
                        (Worker.phone == w_data["phone"]) | (Worker.email == w_data["email"])
                    ).first()
                    if not existing:
                        db.add(Worker(
                            name=w_data["name"],
                            email=w_data["email"],
                            phone=w_data["phone"],
                            password_hash=hash_password(w_data["password"]),
                            zone=w_data["zone"],
                            ward=w_data["ward"],
                            skills=w_data["skills"],
                            active=True,
                        ))
                db.commit()
        finally:
            db.close()
    except Exception:
        pass

def get_db():
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
