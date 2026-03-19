import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Float

import uuid


app = FastAPI(title="BART Incident Classifier & Dashboard API")



from inference import (
    build_query,
    chat_with_media,
    get_extension,
    invoke_url,
    kSupportedList,
)
"""
from gemini_inference import (
    build_query,
    chat_with_media,
    get_extension,
    invoke_url,
    kSupportedList,
)"""


# DATABASE CONFIGURATION
DATABASE_URL = "postgresql://postgres:CSE_312!@localhost:5432/bart_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    evidence_id = Column(Integer, primary_key=True, autoincrement=True)  
    submission_id = Column(String)
    incident_id = Column(String, ForeignKey("incidents.incident_id"))
    image_url = Column(String)
    embedding = Column(String)
    submitted_at = Column(DateTime)
    user_context = Column(String)
    found_priority = Column(String)

# Create the tables in Postgres if they don't exist
Base.metadata.create_all(bind=engine)

# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# API ENDPOINTS
@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/submissions")
async def submissions(
    media: list[UploadFile] = File(default=[]),
    description: str = Form(default=None),
):
    tmp_paths: list[Path] = []
    db = SessionLocal() # Start DB Session
    try:
        # 1. Save uploaded files to temp storage
        for upload in media:
            ext = get_extension(upload.filename or "")
            suffix = f".{ext}"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(await upload.read())
            tmp.close()
            tmp_paths.append(Path(tmp.name))

        # 2. Get the VLM Classification
        query = build_query(description)
        result = chat_with_media(
            invoke_url, [str(p) for p in tmp_paths], query,
            description=description,
        )

        if not result:
            raise HTTPException(status_code=500, detail="VLM failed to respond")

        # 3. Store the report in Postgres
        new_report = PhotoReport(
            submission_id=str(uuid.uuid4())[:8],
            incident_id="1",  # <--- THIS IS THE LINK. Hardcoded to '2'                     #hardcoded
            image_url="test_outlet.jpg",                                                    #hardcoded
            submitted_at=datetime.utcnow(),
            user_context=description or "No description provided",
            found_priority="medium",                                                        #hardcoded
            embedding=None                                                                  #hardcoded
        )
        
        db.add(new_report)
        db.commit() 

        return result

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
        for p in tmp_paths:
            p.unlink(missing_ok=True)


# Dashboard - get incidents
@app.get("/api/incidents")
async def get_incidents():
    db = SessionLocal()
    try:
        return db.query(Incident).all()
    finally:
        db.close()

# Dashboard - get reports
@app.get("/api/photo-reports/{incident_id}")
async def get_evidence(incident_id: str):
    db = SessionLocal()
    try:
        reports = db.query(PhotoReport).filter(PhotoReport.incident_id == incident_id).all()
        return reports
    finally:
        db.close()