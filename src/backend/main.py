import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.backend.database import Base, Incident, PhotoReport, engine, get_db
from src.backend.inference import (
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

        submission_id = uuid.uuid4().hex
        incident_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)

        incident = Incident(
            incident_id=incident_id,
            status="New",           
            issue_priority=None,
            discipline=None,
            vlm_summary=description or None,
            location_id=None,
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
                submission_id=submission_id,
                incident_id=incident_id,
                image_url=saved_image_url,
                embedding=None,
                submitted_at=now,
                user_context=description,
                found_priority="Standard",
            )
            db.add(photo_report)

        db.commit()

        return {
            "incident_id": incident_id,
            "submission_id": submission_id,
            "description": description,
            "timestamp": now.isoformat(),
        }
    finally:
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