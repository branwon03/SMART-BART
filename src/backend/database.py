import os
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
)
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set (check .env)")

# Docker Compose: .env often points at localhost for host-side tools; Postgres service is `db`.
_use_internal = os.getenv("DATABASE_USE_INTERNAL_DB", "").lower() in ("1", "true", "yes")
if _use_internal and not DATABASE_URL.startswith("sqlite"):
    _parsed = make_url(DATABASE_URL)
    if _parsed.host in ("localhost", "127.0.0.1", "::1"):
        DATABASE_URL = str(_parsed.set(host="db"))

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
