"""
This module contains the main processing logic for incoming photo reports. It performs the following steps:
1. Periodically polls the database for new photo reports that haven't been processed yet.
2. For each new photo report, it resolves the local image path and checks if geolocation is needed.
3. If geolocation is requested, it extracts GPS data from the image and determines the nearest BART station.
4. It then calls the Gemini VLM model to classify the issue and generate an embedding for the photo.
5. After processing all photos in a submission, it uses the highest-confidence photo's embedding to find a matching incident.
6. It assigns all photos in the submission to the matched incident (or a new one if no match is found).
7. Finally, it promotes the best photo's metadata to the incident level if it has the highest confidence.
"""

import os
import time
import math
import mimetypes
from datetime import datetime
from pathlib import Path
from sqlalchemy import func, text
from src.backend.database import (
    Base,
    engine,
    SessionLocal,
    PhotoReport,
    Incident,
    ensure_reporter_columns_on_photo_reports,
    ensure_image_blob_columns_on_photo_reports,
)
from dotenv import load_dotenv
from google import genai
from typing import cast
from google.genai import types
from google.genai.types import GenerateContentConfig
from google.oauth2 import service_account
from sqlalchemy.orm import Session
from src.backend.inference import generate_embedding
from src.backend.gemini_parser import parse_classification, DISCIPLINES
from src.backend.grouping import find_matching_incident  # , GROUPING_THRESHOLD
from src.backend.gps_lookup import get_nearest_station_local

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

_genai_client: genai.Client | None = None


def get_genai_client():
    """Vertex client using a service account file (same pattern as inference.py), not host-only ADC."""
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"

    if not use_vertex or not project:
        raise RuntimeError(
            "Gemini/Vertex is not configured. Set GOOGLE_GENAI_USE_VERTEXAI=true and GOOGLE_CLOUD_PROJECT."
        )

    key_path = os.path.expanduser(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
    )
    creds_path = Path(key_path)
    if not creds_path.is_file():
        raise FileNotFoundError(
            f"Vertex AI credentials not found at {creds_path.resolve()}. "
            "Set GOOGLE_APPLICATION_CREDENTIALS or add credentials.json (e.g. mount it in Docker)."
        )
    credentials = service_account.Credentials.from_service_account_file(
        str(creds_path),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return genai.Client(
        vertexai=True,
        project=project,
        location=location,
        credentials=credentials,
    )


def resolve_local_image_path(photo: PhotoReport) -> str:
    image_url = getattr(photo, "image_url", None)
    evidence_id = getattr(photo, "evidence_id", None)
    blob = getattr(photo, "image_blob", None)

    if blob and evidence_id:
        work = Path(UPLOAD_DIR) / ".blob_work"
        work.mkdir(parents=True, exist_ok=True)
        mime = getattr(photo, "image_mime", None) or ""
        low = mime.lower()
        if "png" in low:
            ext = ".png"
        elif "webp" in low:
            ext = ".webp"
        else:
            ext = ".jpg"
        path = work / f"{evidence_id}{ext}"
        path.write_bytes(bytes(blob))
        return str(path)

    # Test path / legacy local path case: image_url is a plain filename like "photo1.jpg"
    if (
        image_url
        and isinstance(image_url, str)
        and not image_url.startswith("/api/images/")
    ):
        return os.path.join(str(UPLOAD_DIR), image_url)

    # Real app case: image_url is "/api/images/{evidence_id}", so resolve from evidence_id on disk
    if evidence_id:
        matches = list(Path(UPLOAD_DIR).glob(f"{evidence_id}.*"))
        if matches:
            return str(matches[0])

    return ""


def identify_objects(
    image_path: str, class_list: list, user_description: str = "Not provided"
) -> tuple[str, float]:
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
        You are a BART agent classifying objects given an image and/or text description, submitted by a train commuter to the maintenance routing system.
        You should assign the priority level in the way a large scale transit agency would.

        The Logic Rule: If it exists, treat the User Description as the primary evidence for the object's functional state. Even if the image appears visually NOMINAL (clean/intact),
        if the user describes a functional failure (e.g., flickering, strange noises, 'stuck' buttons), you must treat the situation as an active issue.
        The object you should visually focus on is most likely located in the center of the image.
        Since the user has submitted a report, assume that the object is in some way not functioning as intended.
        If the image pertains to an emergency blue phone, fire sprinkler, or exit signage, assign CRITICAL priority regardless of visual state or user description.
        Otherwise, if the image appears visually NOMINAL but there is NO user description, assign a LOW priority
        Overflowing garbage cans are HIGH priority.
        Card scanners are always MEDIUM priority, unless the user prompt mentions that several scanners are out, in which case, the priority should be set to HIGH.
        Faded road markings are always either LOW or MEDIUM priority.
   
        - FARE COLLECTION: Card scanners (they are colored black)
        - BUILDINGS: Cracked ground, Cracked floors, cracked walls, water intrusion, faded paint, vandalism, doors, missing signs, drainage issues
        - COMMS: Emergency telephones, electronic destination signs
        - ELEVATOR AND ESCALATOR: All elevator and escalator related issues (except cleaning — that is System Service)
        - GROUNDS: Landscaping, fencing, maintaining outdoor spaces, grass, trimming, irrigation systems, tree removals. Faded road paint and grounds cracks DO NOT BELONG IN THIS DISCIPLINE, they belong in BUILDINGS.
        - MECHANICAL: Fire suppression (sprinklers, extinguishers), piping (water, in/out of station), HVAC, ventilation fans
        - SYSTEM SERVICE: Garbage collection, spills on floors, bathroom cleaning
        - ELECTRICAL: Lights, light switches, electrical plugs, exposed cables, anything related to electrical systems
        - UNCLASSIFIED: If the issue cannot be confidently classified into any of the above disciplines, choose this pseudo-discipline
        
        Return exactly these 3 lines and nothing else:
        discipline: <one label from the list above>
        issue_priority: <LOW|MEDIUM|HIGH|CRITICAL>
        vlm_summary: <Describe the type of object in 3 words or less. Append "broken", "disfunctional", "giving error", "flickering", "stuck", "overflowing", or 
            another relevant one word adjective that is NOT "nominal" or "working" even if the object appears visually fine, since the user submitted a report which indicates a functional issue.>

        USER DESCRIPTION: {user_description}
        """.strip()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=GenerateContentConfig(
            response_mime_type="application/json", response_logprobs=True, logprobs=3
        ),
    )

    raw_response = (response.text or "").strip()

    if not raw_response:
        raise ValueError("Gemini returned an empty response")

    # Calculate discipline selection confidence
    discipline_conf = 0.0
    try:
        candidate = response.candidates[0]
        logprobs_list = candidate.logprobs_result.chosen_candidates

        # Look for the token representing the VALUE of the "discipline" key
        for i, lp in enumerate(logprobs_list):
            token_clean = lp.token.strip().replace('"', "").upper()
            # Find where the model starts outputting the discipline value
            if "DISCIPLINE" in token_clean:
                # In JSON, the value usually follows after a quote/colon within 5 tokens
                for offset in range(1, 6):
                    if i + offset >= len(logprobs_list):
                        break
                    val_token = (
                        logprobs_list[i + offset].token.strip().replace('"', "").upper()
                    )
                    if any(d in val_token for d in DISCIPLINES if d != "UNCLASSIFIED"):
                        discipline_conf = math.exp(logprobs_list[i + offset].log_prob)
                        print(
                            f"  [debug] Found surgical JSON token '{val_token}' Confidence: {discipline_conf:.2f})"
                        )
                        break
                    if discipline_conf > 0:
                        break

        # Fallback to incase extraction is messy
        if discipline_conf == 0.0:
            avg_lp = candidate.avg_logprobs or -1.0
            discipline_conf = math.exp(avg_lp) ** (1 / len(logprobs_list))

    except Exception as e:
        print(f" [!] Surgical parsing error: {e}. Defaulting to safety.")
        discipline_conf = 0.50

    return raw_response, min(discipline_conf, 1.0)


def process_submission(submission_id: str, db: Session):
    """
    Processes all photos belonging to a single submission together.
    All photos in a submission are guaranteed to end up in the same incident.
    """
    photos = (
        db.query(PhotoReport)
        .filter(PhotoReport.submission_id == submission_id)
        .filter(PhotoReport.photo_report_status == "New")
        .with_for_update(skip_locked=True)
        .all()
    )

    if not photos:
        print(f"[!] No new photos found for submission {submission_id}")
        return

    print(f"[*] Processing submission {submission_id} ({len(photos)} photo(s))")

    # --- Phase 1: Classify and embed every photo in the submission ---
    # We need embeddings before we can do any similarity matching.

    results = []

    for photo in photos:
        file_path = resolve_local_image_path(photo)
        description = getattr(photo, "user_context", None) or "Not provided"

        if not file_path or not os.path.exists(file_path):
            print(f"[!] File not found for photo {photo.evidence_id}: {file_path}")
            photo.photo_report_status = "Error: File Missing"  # type: ignore[assignment]
            db.commit()
            continue

        # Check if geolocation is needed
        if photo.photo_location_id == "Assign-Me-Via-Geolocation":
            print(
                f"[*] Geolocation requested for {photo.evidence_id}. Extracting EXIF..."
            )
            found_location = get_nearest_station_local(file_path)
        else:
            # Keep the manually provided ID (e.g., from a dropdown or user selection)
            found_location = photo.photo_location_id
            print(f"[*] Using provided location ID: {found_location}")

        photo.photo_location_id = found_location  # type: ignore[assignment]
        photo.photo_report_status = "In-Progress"  # type: ignore[assignment]
        db.commit()

        try:
            # call identify_object for this photo_report
            raw_response, confidence = identify_objects(
                file_path, DISCIPLINES, user_description=description
            )
            parsed = parse_classification(raw_response)
            if confidence < 0.45:
                print(
                    f"  [!] Low discipline confidence ({confidence:.2f}). Forcing UNCLASSIFIED."
                )
                parsed["discipline"] = "UNCLASSIFIED"

            embedding_instruction = (
                f"Task: Grouping maintenance photos from different angles. "
                f"Physical Asset: {parsed['vlm_summary']}. "
                f"Location Context: {parsed['discipline']} area. "
                f"Instruction: Identify the specific physical asset and scene. "
                f"Focus on spatial surroundings and object geometry. "
                f"Ignore lighting, blur, or camera quality."
            )

            print(f"[*] Generating multimodal embedding for {photo.evidence_id}...")
            vector = generate_embedding(
                text=embedding_instruction, image_paths=[Path(file_path)]
            )

            # Update the PhotoReport with the results
            photo.vlm_summary = parsed["vlm_summary"]
            photo.photo_report_discipline = parsed["discipline"]
            photo.embedding = vector
            photo.found_priority = parsed["issue_priority"]
            photo.photo_report_status = "Completed"  # type: ignore[assignment]
            photo.photo_report_confidence = confidence  # type: ignore[assignment]

            db.commit()
            results.append((photo, parsed, confidence, vector, found_location))
            print(
                f"  [+] Classified {photo.evidence_id}: {parsed['discipline']} (conf: {confidence:.2f})"
            )

        except Exception as e:
            print(f"[!] Error classifying photo {photo.evidence_id}: {e}")
            photo.photo_report_status = "Error: Inference Failed"  # type: ignore[assignment]
            db.commit()

    if not results:
        print(
            f"[!] No photos were successfully classified for submission {submission_id}"
        )
        return

    # --- Phase 2: Find the best incident match for the WHOLE submission ---
    # Use the highest-confidence photo's embedding as the submission's
    # "representative" signal for similarity search. This means one strong
    # photo can anchor the whole submission to an existing incident.

    best_photo, best_parsed, best_confidence, best_vector, best_location = max(
        results, key=lambda x: x[2]
    )

    raw_time = best_photo.submitted_at
    if isinstance(raw_time, str):
        try:
            cleaned_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        except ValueError:
            cleaned_time = datetime.now()
    else:
        cleaned_time = raw_time

    target_incident_id, match_score = find_matching_incident(
        db,
        new_embedding=best_vector,
        discipline=best_parsed["discipline"],
        location_id=cast(str | None, best_photo.photo_location_id),
        submitted_at=cleaned_time,
        exclude_evidence_id=cast(str | None, best_photo.evidence_id),
    )

    safe_match_score = match_score if match_score is not None else 0.0 #This ensures we don't print "None" and cause an error

    if target_incident_id:
        print(f"  [+] Best match for submission {submission_id} is Incident {target_incident_id} with score {safe_match_score:.3f}")
    else:
        target_incident_id = photos[0].incident_id
        print(f"  [-] No match (best score={safe_match_score:.3f}). Using new Incident {target_incident_id}.")

    # --- Phase 3: Assign every photo to the target incident ---

    for photo, parsed, confidence, vector, found_location in results:
        original_incident_id = photo.incident_id

        if photo.incident_id != target_incident_id:
            photo.incident_id = target_incident_id
            db.commit()

            # Clean up the now-empty placeholder incident
            try:
                db.execute(
                    text("""
                        DELETE FROM incidents
                        WHERE incident_id = :old_id
                        AND NOT EXISTS (
                            SELECT 1 FROM photo_reports WHERE incident_id = :old_id
                        )
                    """),
                    {"old_id": original_incident_id},
                )
                db.commit()
            except Exception as delete_error:
                print(
                    f" [!] Failed to delete original incident {original_incident_id}: {delete_error}"
                )
                db.rollback()

        photo.photo_report_status = "Completed"  # type: ignore[assignment]
        db.commit()

    # --- Phase 4: Promote the best photo's metadata to the incident ---
    incident = (
        db.query(Incident).filter(Incident.incident_id == target_incident_id).first()
    )

    if incident:
        current_max_confidence = (
            db.query(func.max(PhotoReport.photo_report_confidence))
            .filter(PhotoReport.incident_id == target_incident_id)
            .filter(PhotoReport.evidence_id != best_photo.evidence_id)
            .scalar()
            or -1.0
        )

        # If this photo is the most confident one we've seen for this incident,
        # promote its metadata to the incident level.
        if best_confidence > current_max_confidence:
            incident.discipline = best_parsed["discipline"]
            incident.vlm_summary = best_parsed["vlm_summary"]
            incident.issue_priority = best_parsed["issue_priority"]

            db.commit()
            print(
                f"  [✓] Updated Incident {target_incident_id} -> "
                f"{best_parsed['discipline']} | {best_parsed['issue_priority']}"
            )

        else:
            print(
                f"  [-] Incident {target_incident_id} already has a higher-confidence classification. Skipping update."
            )

        # Propagate resolved location to incident if it hasn't been set yet
        current_inc_loc = getattr(incident, "location_id", None)
        if current_inc_loc == "Assign-Me-Via-Geolocation" or current_inc_loc is None:
            incident.location_id = best_location
            db.commit()
            print(f"  [✓] Updated Incident {target_incident_id} location -> {best_location}")

BATCH_SIZE = 10 

def run_processor():
    print("[*] Initializing database foundation...")
    try:
        with engine.connect() as conn:
            # 1. Enable pgvector (required for your embeddings)
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("[*] pgvector extension enabled.")

        # 2. Create the tables if they don't exist
        Base.metadata.create_all(bind=engine)
        ensure_reporter_columns_on_photo_reports()
        ensure_image_blob_columns_on_photo_reports()
        print("[*] Database tables created/verified.")

    except Exception as e:
        print(f"[!] Initialization failed: {e}")
        # If DB isn't ready, wait 5 seconds and let Docker restart the container
        time.sleep(5)
        return

    while True:
        db = SessionLocal()
        try:
            # Look for the next photo that hasn't been processed yet
            pending = (
                db.query(PhotoReport.submission_id)
                .filter(PhotoReport.photo_report_status == "New")
                .distinct()
                .limit(BATCH_SIZE)
                .all()
            )

            if pending:
                for (submission_id,) in pending:
                    try:
                        process_submission(submission_id, db)
                    except Exception as e:
                        print(f"[!] Error processing submission {submission_id}: {e}")

            else:
                print("[~] No new submissions. Waiting...")
                time.sleep(10)
        except Exception as e:
            print(f"[!] Processor error: {e}")
            time.sleep(5)

        finally:
            db.close()


if __name__ == "__main__":
    run_processor()
