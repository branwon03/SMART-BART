import os
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

REMOTE_DATABASE_URL = "postgresql://neondb_owner:npg_2wK7VUOsuIzL@ep-dry-feather-aeb6o61w-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", REMOTE_DATABASE_URL)
    return re.sub(r"^postgresql://", "postgresql+psycopg://", database_url)


REMOTE_DATABASE_URL = get_database_url()

engine = create_engine(REMOTE_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ── Schema ────────────────────────────────────────────────────────────────────

class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(String, primary_key=True)
    status = Column(String)
    issue_priority = Column(String)
    discipline = Column(String)
    vlm_summary = Column(String)
    location_id = Column(String)
    created_at = Column(DateTime)


class PhotoReport(Base):
    __tablename__ = "photo_reports"

    evidence_id = Column(String, primary_key=True)
    submission_id = Column(String)
    incident_id = Column(String, ForeignKey("incidents.incident_id"))
    image_url = Column(String)
    embedding = Column(String)
    submitted_at = Column(DateTime)
    user_context = Column(String)
    found_priority = Column(String)


# ── Dependency for FastAPI ────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
