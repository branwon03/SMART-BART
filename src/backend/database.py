import os
from datetime import datetime
from pathlib import Path
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set (check .env)")

# pgvector.Vector is not used for SQLite (tests / local without Postgres).
_USE_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ── Models ────────────────────────────────────────────────────────────────────

class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(String, primary_key=True)
    status = Column(String)
    issue_priority = Column(String)
    discipline = Column(String)
    vlm_summary = Column(String)
    location_id = Column(String)
    created_at = Column(DateTime)
    last_report_at: Mapped[datetime | None] = mapped_column(DateTime)
    gmail_thread_id = Column(String, nullable=True, index=True)


class PhotoReport(Base):
    __tablename__ = "photo_reports"

    evidence_id = Column(String, primary_key=True)
    incident_id = Column(String, ForeignKey("incidents.incident_id"))
    submission_id = Column(String, index=True) 
    image_url = Column(String)
    embedding = Column(JSON if _USE_SQLITE else Vector(3072))
    submitted_at = Column(DateTime)
    user_context = Column(String)
    found_priority = Column(String)
    vlm_summary = Column(String)
    photo_report_status = Column(String)
    photo_report_confidence = Column(Float, nullable=True)
    photo_report_discipline = Column(String, nullable=True)
    photo_location_id = Column(String)


# ── Dependency for FastAPI ────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)


def refresh_incident_last_report_at(db: Session, incident_id: str) -> None:
    """Set last_report_at from photo_reports: max date iff min/max fall on different UTC days."""
    inc = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not inc:
        return
    min_date = (
        db.query(func.min(PhotoReport.submitted_at))
        .filter(PhotoReport.incident_id == incident_id)
        .scalar()
    )
    max_date = (
        db.query(func.max(PhotoReport.submitted_at))
        .filter(PhotoReport.incident_id == incident_id)
        .scalar()
    )
    if min_date and max_date and min_date.date() != max_date.date():
        inc.last_report_at = max_date
    else:
        inc.last_report_at = None
