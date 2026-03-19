import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# New imports for Database connection
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

"""
from inference import (
    build_query,
    chat_with_media,
    get_extension,
    invoke_url,
    kSupportedList,
)
"""

app = FastAPI(title="BART Incident Classifier & Dashboard API")

# --- DATABASE CONFIGURATION ---
DATABASE_URL = "postgresql://postgres:CSE_312!@localhost:5432/bart_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the Incident Table Schema
class Incident(Base):
    __tablename__ = "incidents"
    incident_id = Column(String, primary_key=True, index=True)
    location_id = Column(String)
    discipline = Column(String)
    status = Column(String)
    vlm_summary = Column(String)
    issue_priority = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create the tables in Postgres if they don't exist
Base.metadata.create_all(bind=engine)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- COMMENTED OUT MOCK DATA (FOR REFERENCE) ---
"""
now = datetime.now()
incidents = [
    {"incident_id": "1", "location_id": "Montgomery St", "discipline": "Electrical", "status": "In Progress", "vlm_summary": "Dysfunctional outlet in ticket office", "issue_priority": 1, "created_at": (now - timedelta(minutes=30)).isoformat()},
    {"incident_id": "2", "location_id": "Powell St", "discipline": "Fare Collection", "status": "In Progress", "vlm_summary": "Broken outlet in office", "issue_priority": 2, "created_at": (now - timedelta(hours=1)).isoformat()},
]

photo_reports = [
    {"evidence_id": "ev1", "incident_id": "1", "image_url": "/mock_outlet_1.jpg", "user_context": "the outlet doesn't work", "user_priority": "medium"},
    {"evidence_id": "ev2", "incident_id": "1", "image_url": "/mock_outlet_1.jpg", "user_context": "The top socket does not work", "user_priority": "medium"},
    {"evidence_id": "ev3", "incident_id": "2", "image_url": "/mock_scanner_1.jpg", "user_context": "Scanner is not turning on", "user_priority": "low"},
    {"evidence_id": "ev4", "incident_id": "2", "image_url": "/mock_scanner_1.jpg", "user_context": "out of service", "user_priority": "low"},
    {"evidence_id": "ev5", "incident_id": "2", "image_url": "/mock_scanner_1.jpg", "user_context": "not scanning", "user_priority": "medium"}
]
"""

# --- API ENDPOINTS ---

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/submissions")
async def submissions(
    media: list[UploadFile] = File(default=[]),
    description: str = Form(default=None),
):
    # This logic still requires the 'inference' imports to be uncommented to work
    tmp_paths: list[Path] = []
    try:
        for upload in media:
            # Note: get_extension and kSupportedList come from inference.py
            ext = get_extension(upload.filename or "")
            if ext not in kSupportedList:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unsupported file type '.{ext}'. Accepted: {', '.join(sorted(kSupportedList))}",
                )

            suffix = f".{ext}"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(await upload.read())
            tmp.close()
            tmp_paths.append(Path(tmp.name))

        query = build_query(description)
        result = chat_with_media(
            invoke_url, [str(p) for p in tmp_paths], query,
            description=description,
        )
        return result
    finally:
        for p in tmp_paths:
            p.unlink(missing_ok=True)

# Dashboard endpoints updated to use the DB
@app.get("/api/incidents")
async def get_incidents():
    db = SessionLocal()
    try:
        # Fetches all rows from the Postgres 'incidents' table
        return db.query(Incident).all()
    finally:
        db.close()

@app.get("/api/photo-reports/{incident_id}")
async def get_evidence(incident_id: str):
    # Keeping this as a mock return for now until you create a PhotoReport table
    return [
        {"evidence_id": "ev1", "incident_id": incident_id, "image_url": "/logo.png", "user_context": "Database report linked successfully.", "user_priority": "medium"}
    ]