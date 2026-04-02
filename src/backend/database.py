import os
import re
from pathlib import Path
from pgvector.sqlalchemy import Vector
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
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


class PhotoReport(Base):
    __tablename__ = "photo_reports"

    evidence_id = Column(String, primary_key=True)
    submission_id = Column(String)
    incident_id = Column(String, ForeignKey("incidents.incident_id"))
    image_url = Column(String)
    embedding = Column(Vector(3072))
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
