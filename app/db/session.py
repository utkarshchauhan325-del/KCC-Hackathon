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

def get_db():
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
