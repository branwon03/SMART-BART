import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

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
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _normalize_database_url(url: str) -> str:
    """Default postgresql:// → psycopg2 driver in SQLAlchemy; deps only have psycopg3."""
    raw = url.strip()
    if not raw:
        return raw
    parsed = urlparse(raw)
    scheme = parsed.scheme.lower()

    if scheme.startswith("sqlite"):
        return raw

    if scheme in ("postgresql", "postgres"):
        return urlunparse(parsed._replace(scheme="postgresql+psycopg"))

    if scheme == "postgresql+psycopg2":
        return urlunparse(parsed._replace(scheme="postgresql+psycopg"))

    return raw


env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)
_raw_database_url = os.getenv("DATABASE_URL")
if not _raw_database_url:
    raise RuntimeError("DATABASE_URL is not set (check .env)")

DATABASE_URL = _normalize_database_url(_raw_database_url)

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
