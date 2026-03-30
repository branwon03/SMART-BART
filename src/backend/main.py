import os
import shutil
import tempfile
import uuid
import re
from datetime import datetime
from pathlib import Path
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.backend.database import Base, Incident, PhotoReport, engine, get_db
from src.backend.inference import (
    build_query,
    chat_with_media,
    get_extension,
    kSupportedList,
)

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="BART Incident Classifier & Dashboard API")

@app.on_event("startup")
def _startup_create_tables() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"[startup] create_all failed: {exc}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def parse_vlm_response(raw_text: str):
    """
    Parses 'Discipline: ELECTRICAL, Priority Level: CRITICAL...' 
    into a clean dictionary using regex.
    """
    data = {"discipline": "UNKNOWN", "priority": "Standard", "summary": raw_text}
    
    try:
        # Regex to capture text between the labels and commas
        disc_match = re.search(r"Discipline:\s*([^,]+)", raw_text, re.IGNORECASE)
        pri_match = re.search(r"Priority Level:\s*([^,]+)", raw_text, re.IGNORECASE)
        sum_match = re.search(r"Brief Summary:\s*(.+)", raw_text, re.IGNORECASE)

        if disc_match:
            data["discipline"] = disc_match.group(1).strip().upper()
        if pri_match:
            data["priority"] = pri_match.group(1).strip()
        if sum_match:
            data["summary"] = sum_match.group(1).strip()
    except Exception:
        pass 
        
    return data

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/submissions")
async def submissions(
    media: list[UploadFile] = File(default=[]),
    description: str = Form(default=None),
    db: Session = Depends(get_db),
):
    tmp_paths: list[Path] = []
    try:
        # 1. Save uploaded files to temp storage for processing
        for upload in media:
            ext = get_extension(upload.filename or "")
            if ext not in kSupportedList:
                raise HTTPException(status_code=422, detail="Unsupported file type")
            
            suffix = f".{ext}"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(await upload.read())
            tmp.close()
            tmp_paths.append(Path(tmp.name))

        # 2. Run Inference
        submission_id = uuid.uuid4().hex
        query_text = build_query(description)
        result = chat_with_media(tmp_paths, query_text)

        if result is None:
            raise HTTPException(status_code=502, detail="Inference API unavailable")

        # 3. Parse the long string from Gemini into clean fields
        parsed_data = parse_vlm_response(result["discipline"])
        
        incident_id = uuid.uuid4().hex
        evidence_id = uuid.uuid4().hex
        now = datetime.utcnow()

        # 4. Save the first image to permanent storage
        saved_image_url = None
        if tmp_paths:
            first = tmp_paths[0]
            dest = UPLOAD_DIR / f"{evidence_id}{first.suffix}"
            shutil.copy2(str(first), str(dest))
            saved_image_url = f"/api/images/{evidence_id}"

        # 5. Save to Database
        incident = Incident(
            incident_id=incident_id,
            status="Open",
            issue_priority=parsed_data["priority"],
            discipline=parsed_data["discipline"],
            vlm_summary=parsed_data["summary"],
            location_id=None,
            created_at=now,
        )
        
        photo_report = PhotoReport(
            evidence_id=evidence_id,
            submission_id=submission_id,
            incident_id=incident_id,
            image_url=saved_image_url,
            embedding=None,
            submitted_at=now,
            user_context=description,
            found_priority=parsed_data["priority"],
        )

        db.add(incident)
        db.add(photo_report)
        db.commit()

        # 6. Return Clean Response
        return {
            "incident_id": incident_id,
            "submission_id": submission_id,
            "discipline": parsed_data["discipline"],
            "priority": parsed_data["priority"],
            "summary": parsed_data["summary"],
            "description_provided": description,
            "timestamp": now.isoformat()
        }
    finally:
        # Cleanup temp files
        for p in tmp_paths:
            p.unlink(missing_ok=True)

@app.get("/api/incidents")
async def get_incidents(db: Session = Depends(get_db)):
    return db.query(Incident).all()

@app.get("/api/photo-reports/{incident_id}")
async def get_photo_reports(incident_id: str, db: Session = Depends(get_db)):
    return (
        db.query(PhotoReport)
        .filter(PhotoReport.incident_id == incident_id)
        .all()
    )

MIME_MAP = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}

@app.get("/api/images/{evidence_id}")
async def get_image(evidence_id: str):
    for ext, mime in MIME_MAP.items():
        path = UPLOAD_DIR / f"{evidence_id}.{ext}"
        if path.is_file():
            return FileResponse(path, media_type=mime)
    raise HTTPException(status_code=404, detail="Image not found")