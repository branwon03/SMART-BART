import os
import time
import math
import mimetypes
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig
from sqlalchemy.orm import Session

from src.backend.database import SessionLocal, Incident, PhotoReport
from src.backend.gemini_parser import parse_classification, DISCIPLINES
 
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

def get_genai_client():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"

    if not use_vertex or not project:
        raise RuntimeError(
            "Gemini/Vertex is not configured. Set GOOGLE_GENAI_USE_VERTEXAI=true and GOOGLE_CLOUD_PROJECT."
        )

    return genai.Client(
        vertexai=True,
        project=project,
        location=location,
    )

def resolve_local_image_path(photo: PhotoReport) -> str:
    image_url = getattr(photo, "image_url", None)
    evidence_id = getattr(photo, "evidence_id", None)

    # Test path / legacy local path case: image_url is a plain filename like "photo1.jpg"
    if image_url and isinstance(image_url, str) and not image_url.startswith("/api/images/"):
        return os.path.join(str(UPLOAD_DIR), image_url)

    # Real app case: image_url is "/api/images/{evidence_id}", so resolve from evidence_id on disk
    if evidence_id:
        matches = list(Path(UPLOAD_DIR).glob(f"{evidence_id}.*"))
        if matches:
            return str(matches[0])

    return ""

def identify_objects(image_path: str, class_list: list) -> tuple[str, float]:
    """
    Gemini 2.5 Flash call with logprobs for real confidence scoring.

    Returns:
    - raw structured text response for parse_classification(...)
    - confidence score derived from avg_logprobs
    """
    print(f"  [model] Running inference on {os.path.basename(image_path)}")

    client = get_genai_client()

    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/jpeg"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    prompt = f"""
You are classifying a BART maintenance incident from an image.

Choose exactly ONE discipline from:
{", ".join(class_list)}

Return exactly these 3 lines and nothing else:
discipline: <one label from the list above>
issue_priority: <LOW|MEDIUM|HIGH|CRITICAL>
vlm_summary: <one concise sentence>
""".strip()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=GenerateContentConfig(response_logprobs=True, logprobs=3)
    )

    raw_response = (response.text or "").strip()

    if not raw_response:
        raise ValueError("Gemini returned an empty response")

    #converting the log probs to a confidence score
    avg_logprobs = response.candidates[0].avg_logprobs or 0.0
    confidence = math.exp(avg_logprobs)

    return raw_response, confidence

def process_incident(incident: Incident, db: Session):
    #runs the full pipeline for a single incident: selection -> lock -> model loop -> parse -> map -> save

    incident_id = incident.incident_id

    incident.status = "In-Progress"  # type: ignore[assignment]
    db.commit()
    print(f"[*] Incident {incident_id} locked as In-Progress")

    photos = db.query(PhotoReport).filter(PhotoReport.incident_id == incident_id).all()

    #if no photos exit early
    if not photos:
        print(f"[!] No photos found for incident {incident_id}")
        incident.status = "Error: No Photos"  # type: ignore[assignment]
        db.commit()
        return

    best_category = None
    best_summary = None
    best_priority = None
    best_confidence = -1.0
    missing_files = []

    for photo in photos:
        file_path = resolve_local_image_path(photo)

        if not file_path or not os.path.exists(file_path):
            print(f"[!] File not found: {file_path}")
            missing_files.append(file_path)
            continue

        raw_response, confidence = identify_objects(file_path, DISCIPLINES)
        parsed = parse_classification(raw_response)

        if confidence > best_confidence:
            best_confidence = confidence
            best_category = parsed["discipline"]
            best_summary = parsed["vlm_summary"]
            best_priority = parsed["issue_priority"]
            print(f"  [+] New best result: {best_category} (confidence: {confidence:.2f})")

    all_missing = len(missing_files) == len(photos)

    if all_missing:
        incident.status = "Error: All Files Missing"  # type: ignore[assignment]
        print(f"[!] All files missing for incident {incident_id}")

    elif best_category is None:
        incident.status = "Error: Model Returned No Results"  # type: ignore[assignment]
        print(f"[!] Model returned no results for incident {incident_id}")

    else:
        incident.discipline = best_category  # type: ignore[assignment]
        incident.vlm_summary = best_summary  # type: ignore[assignment]
        incident.issue_priority = best_priority  # type: ignore[assignment]
        incident.status = "Completed"  # type: ignore[assignment]
        print(f"  [✓] Incident {incident_id} -> {best_category} | {best_priority} (confidence: {best_confidence:.2f})")

    db.commit()

def run_processor():
    print("[*] Starting Incident Processor...")

    while True:
        db = SessionLocal()

        try:
            incident = db.query(Incident).filter(Incident.status == "New").first()

            if incident:
                print(f"\n[*] Found New Incident: {incident.incident_id}")
                process_incident(incident, db)

            else:
                print("[~] No new incidents. Waiting...")

        except Exception as e:
            print(f"[!] Unexpected error: {e}")
            try:
                incident.status = "Error: Processing Failed"
                db.commit()
            except Exception:
                db.rollback()

        finally:
            db.close()
    
        time.sleep(10)

if __name__ == "__main__":
    run_processor()
