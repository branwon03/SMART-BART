import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#  Mock Data for Dashboard
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

# Existing Team Endpoints 
@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/submissions")
async def submissions(
    media: list[UploadFile] = File(default=[]),
    description: str = Form(default=None),
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

        query = build_query(description)
        result = chat_with_media(
            invoke_url, [str(p) for p in tmp_paths], query,
            description=description,
        )
        return result
    finally:
        for p in tmp_paths:
            p.unlink(missing_ok=True)


# dashboard endpoints
@app.get("/api/incidents")
async def get_incidents():
    return incidents

@app.get("/api/photo-reports/{incident_id}")
async def get_evidence(incident_id: str):
    return [report for report in photo_reports if report["incident_id"] == incident_id]

# web app endpoints
#...
