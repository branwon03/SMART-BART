import os
import shutil
import tempfile
import uuid
from sqlalchemy import text, func
from typing import cast
from datetime import datetime, timezone
from pathlib import Path
from fastapi.responses import FileResponse, JSONResponse  # Add JSONResponse here
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.backend.database import (
    Base,
    Incident,
    PhotoReport,
    engine,
    ensure_reporter_columns_on_photo_reports,
    get_db,
)
from src.backend.inference import (
    get_extension,
    kSupportedList,
)
from contextlib import asynccontextmanager


class IncidentUpdate(BaseModel):
    issue_priority: str | None = None
    status: str | None = None
    discipline: str | None = None
    location_id: str | None = None
    vlm_summary: str | None = None


class MergePhotosBody(BaseModel):
    evidence_ids: list[str]
class SplitRequest(BaseModel):
    evidence_ids: list[str]
    title: str
    description: str | None = None
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
        ensure_reporter_columns_on_photo_reports()
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
    gmail_thread_id: str = Form(default=None),
    reporter_name: str = Form(default=None),
    reporter_contact: str = Form(default=None),
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
            gmail_thread_id=gmail_thread_id,
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
                photo_location_id=photo_location_id or "EMAIL-Unlocated",
                reporter_name=reporter_name or None,
                reporter_contact=reporter_contact or None,
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
            "gmail_thread_id": r.gmail_thread_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@app.post("/api/incidents/{incident_id}/split")
async def split_incident(
    incident_id: str,
    body: SplitRequest,
    db: Session = Depends(get_db),
):
    parent = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Incident not found")

    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required and cannot be blank")

    order_preserve: list[str] = []
    seen: set[str] = set()
    for eid in body.evidence_ids:
        if eid not in seen:
            seen.add(eid)
            order_preserve.append(eid)

    if not order_preserve:
        raise HTTPException(status_code=422, detail="evidence_ids must not be empty")

    reports = (
        db.query(PhotoReport).filter(PhotoReport.incident_id == incident_id).all()
    )
    by_evidence: dict[str, PhotoReport] = {
        cast(str, r.evidence_id): r for r in reports
    }

    unknown = [eid for eid in order_preserve if eid not in by_evidence]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"evidence_ids not on this incident: {unknown}",
        )

    remaining = len(reports) - len(order_preserve)
    if remaining < 1:
        raise HTTPException(
            status_code=422,
            detail="cannot move all evidence; leave at least one photo on parent incident",
        )

    now = datetime.now(timezone.utc)
    new_incident_id = uuid.uuid4().hex
    new_submission_id = uuid.uuid4().hex

    parent_discipline: str | None = cast(str | None, parent.discipline)
    child_discipline: str | None = parent_discipline
    if body.discipline is not None:
        trimmed_d = body.discipline.strip()
        if trimmed_d:
            child_discipline = trimmed_d

    child = Incident(
        incident_id=new_incident_id,
        status=parent.status,
        issue_priority=parent.issue_priority,
        discipline=child_discipline,
        vlm_summary=title,
        location_id=parent.location_id,
        created_at=now,
    )
    db.add(child)

    desc_provided = body.description is not None
    desc_value = (
        None if body.description is None else (body.description.strip() or None)
    )

    for eid in order_preserve:
        pr = by_evidence[eid]
        setattr(pr, "incident_id", new_incident_id)
        setattr(pr, "submission_id", new_submission_id)
        if desc_provided:
            setattr(pr, "user_context", desc_value)

    db.commit()
    db.refresh(child)

    return {
        "incident_id": child.incident_id,
        "status": child.status,
        "issue_priority": child.issue_priority,
        "discipline": child.discipline,
        "vlm_summary": child.vlm_summary,
        "location_id": child.location_id,
        "created_at": child.created_at.isoformat() if child.created_at else None,
    }


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
    if body.location_id is not None:  
        setattr(row, "location_id", body.location_id)
    if body.vlm_summary is not None:
        title = body.vlm_summary.strip()
        if not title:
            raise HTTPException(
                status_code=422,
                detail="vlm_summary cannot be blank",
            )
        setattr(row, "vlm_summary", title)

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
        SELECT evidence_id, incident_id, image_url, submitted_at, user_context, found_priority, photo_location_id,
               vlm_summary, photo_report_discipline, reporter_name, reporter_contact
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
        vlm_summary_val = row[7]
        photo_report_discipline_val = row[8]
        reporter_name_val = row[9]
        reporter_contact_val = row[10]

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
                "vlm_summary": None
                if vlm_summary_val is None
                else str(vlm_summary_val),
                "photo_report_discipline": None
                if photo_report_discipline_val is None
                else str(photo_report_discipline_val),
                "reporter_name": None
                if reporter_name_val is None
                else str(reporter_name_val),
                "reporter_contact": None
                if reporter_contact_val is None
                else str(reporter_contact_val),
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


@app.post("/api/incidents/{target_incident_id}/merge-photos")
async def merge_photos_into_incident(
    target_incident_id: str,
    body: MergePhotosBody,
    db: Session = Depends(get_db),
):
    target = (
        db.query(Incident)
        .filter(Incident.incident_id == target_incident_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Target incident not found")

    discipline_value = target.discipline

    merged_count = 0
    touched_sources: set[str] = set()
    for eid in body.evidence_ids:
        if not eid:
            continue
        row = (
            db.query(PhotoReport)
            .filter(PhotoReport.evidence_id == eid)
            .first()
        )
        if not row:
            continue
        source_incident_id = cast(str, row.incident_id)
        if source_incident_id == target_incident_id:
            continue
        touched_sources.add(source_incident_id)
        setattr(row, "incident_id", target_incident_id)
        if discipline_value is not None:
            setattr(row, "photo_report_discipline", discipline_value)
        merged_count += 1

    db.flush()

    for src_id in touched_sources:
        if src_id == target_incident_id:
            continue
        remaining = (
            db.query(PhotoReport)
            .filter(PhotoReport.incident_id == src_id)
            .count()
        )
        if remaining == 0:
            orphan = (
                db.query(Incident)
                .filter(Incident.incident_id == src_id)
                .first()
            )
            if orphan:
                db.delete(orphan)

    db.commit()

    return {"merged_count": merged_count}


@app.get("/api/images/{evidence_id}")
def get_image(evidence_id: str):
    for ext in ("png", "jpg", "jpeg", "webp"):
        path = UPLOAD_DIR / f"{evidence_id}.{ext}"
        if path.exists():
            return FileResponse(path, media_type=f"image/{ext}")
    raise HTTPException(status_code=404, detail="Image not found")

@app.get("/api/dashboard/discipline-stats")
async def get_discipline_stats(db: Session = Depends(get_db)):
    """Returns the first and last report dates grouped by discipline."""
    try:
        # We use func.min/max and group_by to aggregate the timestamps
        stats = db.query(
            Incident.discipline,
            func.min(Incident.created_at).label("first_report"),
            func.max(Incident.created_at).label("last_report"),
            func.count(Incident.incident_id).label("total_count")
        ).group_by(Incident.discipline).all()
        
        return [
            {
                "discipline": s.discipline or "Unassigned",
                "first_report": s.first_report.isoformat() if s.first_report else None,
                "last_report": s.last_report.isoformat() if s.last_report else None,
                "total_count": s.total_count
            }
            for s in stats
        ]
    except Exception as e:
        print(f"Dashboard Stats Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard stats")