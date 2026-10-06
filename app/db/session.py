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
    """Create all database tables."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
