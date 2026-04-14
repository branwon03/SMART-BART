import os
import shutil
import tempfile
import uuid
from PIL import Image
from sqlalchemy import text
from datetime import datetime, timezone
from pathlib import Path
from fastapi.responses import FileResponse, JSONResponse  # Add JSONResponse here
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.backend.database import Base, Incident, PhotoReport, engine, get_db
from src.backend.inference import (
    get_extension,
    kSupportedList,
)
from contextlib import asynccontextmanager


class IncidentUpdate(BaseModel):
    issue_priority: str | None = None
    status: str | None = None
    discipline: str | None = None


UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# 1. Define the Lifespan logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    print("Initializing BART Incident Classifier.")
    try:
        # 1. Manually enable the pgvector extension first
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("[startup] pgvector extension enabled.")

        # 2. Now create the tables
        Base.metadata.create_all(bind=engine)
        print("[startup] Database tables created successfully.")

    except Exception as exc:
        print(f"[startup] Initialization failed: {exc}")

    yield


app = FastAPI(title="BART Incident Classifier & Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/submissions")
async def submissions(
    media: list[UploadFile] = File(default=[]),
    description: str = Form(default=None),
    photo_location_id: str = Form(default=None),
    db: Session = Depends(get_db),
):
    tmp_paths: list[Path] = []
    try:
        # 1. Save uploaded files to temp storage for processing
        for upload in media:
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

        # 2. Run Inference
        submission_id = uuid.uuid4().hex
        incident_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)

        incident = Incident(
            incident_id=incident_id,
            status="New",
            issue_priority=None,
            discipline=None,
            vlm_summary=description or None,
            location_id=photo_location_id or None,
            created_at=now,
        )
        db.add(incident)

        for tmp_path in tmp_paths:
            evidence_id = uuid.uuid4().hex
            ext = tmp_path.suffix
            dest = UPLOAD_DIR / f"{evidence_id}{ext}"
            shutil.copy2(str(tmp_path), str(dest))
            saved_image_url = f"/api/images/{evidence_id}"


            photo_report = PhotoReport(
                evidence_id=evidence_id,
                incident_id=incident_id,
                image_url=saved_image_url,
                embedding=None,
                submitted_at=now,
                user_context=description or None,
                found_priority="Standard",
                vlm_summary=None,
                photo_report_status="New",
                photo_report_confidence=None,
                photo_report_discipline=None,
                photo_location_id=photo_location_id,
            )
            db.add(photo_report)

        db.commit()

        # 6. Return Clean Response
        return {
            "incident_id": incident_id,
            "submission_id": submission_id,
            "description": description,
            "timestamp": now.isoformat(),
        }
    finally:
        # Cleanup temp files
        for p in tmp_paths:
            p.unlink(missing_ok=True)


@app.get("/api/incidents")
async def get_incidents(db: Session = Depends(get_db)):
    rows = db.query(Incident).all()
    return [
        {
            "incident_id": r.incident_id,
            "status": r.status,
            "issue_priority": r.issue_priority,
            "discipline": r.discipline,
            "vlm_summary": r.vlm_summary,
            "location_id": r.location_id, 
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@app.put("/api/incidents/{incident_id}")
async def update_incident(
    incident_id: str, body: IncidentUpdate, db: Session = Depends(get_db)
):
    row = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    if body.issue_priority is not None:
        setattr(row, "issue_priority", body.issue_priority)
    if body.status is not None:
        setattr(row, "status", body.status)
    if body.discipline is not None:
        setattr(row, "discipline", body.discipline)

    db.commit()
    db.refresh(row)

    return {
        "incident_id": row.incident_id,
        "status": row.status,
        "issue_priority": row.issue_priority,
        "discipline": row.discipline,
        "vlm_summary": row.vlm_summary,
        "location_id": row.location_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


MIME_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


@app.get("/api/photo-reports/{incident_id}")
async def get_photo_reports(incident_id: str, db: Session = Depends(get_db)):
    # Using a clean dictionary-based query to avoid the 3072-dim vector entirely
    from sqlalchemy import text

    query = text("""
        SELECT evidence_id, incident_id, image_url, submitted_at, user_context, found_priority, photo_location_id
        FROM photo_reports
        WHERE incident_id = :inc_id
        ORDER BY submitted_at DESC
    """)

    result = db.execute(query, {"inc_id": incident_id}).fetchall()

    # Manually building a clean list of standard Python dicts
    clean_data = []
    for row in result:
        image_val = row[2]
        submitted_val = row[3]
        user_context_val = row[4]
        found_pri_val = row[5]

        clean_data.append(
            {
                "evidence_id": str(row[0]),
                "incident_id": str(row[1]),
                "image_url": None if image_val is None else str(image_val),
                "submitted_at": submitted_val
                if isinstance(submitted_val, str)
                else submitted_val.isoformat()
                if submitted_val
                else None,
                "user_context": user_context_val
                if user_context_val is not None
                else "",
                "found_priority": None if found_pri_val is None else str(found_pri_val),
            }
        )
    # Bypass FastAPI's automatic encoder completely
    return JSONResponse(content=clean_data)


@app.delete("/api/incidents/{incident_id}")
async def delete_incident(incident_id: str, db: Session = Depends(get_db)):
    row = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    db.query(PhotoReport).filter(PhotoReport.incident_id == incident_id).delete()
    db.delete(row)
    db.commit()

    return {"deleted_incident_id": incident_id}


@app.get("/api/images/{evidence_id}")
def get_image(evidence_id: str):
    for ext in ("png", "jpg", "jpeg", "webp"):
        path = UPLOAD_DIR / f"{evidence_id}.{ext}"
        if path.exists():
            return FileResponse(path, media_type=f"image/{ext}")
    raise HTTPException(status_code=404, detail="Image not found")
