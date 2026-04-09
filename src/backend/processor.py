import os
import time
import math
import mimetypes
from pathlib import Path
from sqlalchemy import text
from src.backend.database import Base, engine, SessionLocal, PhotoReport
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig
from google.oauth2 import service_account
from sqlalchemy.orm import Session
from src.backend.inference import generate_embedding
from src.backend.database import Incident
from src.backend.gemini_parser import parse_classification, DISCIPLINES
from src.backend.grouping import find_matching_incident#, GROUPING_THRESHOLD
 
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

    # Test path / legacy local path case: image_url is a plain filename like "photo1.jpg"
    if image_url and isinstance(image_url, str) and not image_url.startswith("/api/images/"):
        return os.path.join(str(UPLOAD_DIR), image_url)

    # Real app case: image_url is "/api/images/{evidence_id}", so resolve from evidence_id on disk
    if evidence_id:
        matches = list(Path(UPLOAD_DIR).glob(f"{evidence_id}.*"))
        if matches:
            return str(matches[0])

    return ""

def identify_objects(image_path: str, class_list: list, user_description: str = "Not provided") -> tuple[str, float]:
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
   
        - FARE COLLECTION: Card scanners (they are colored black)
        - BUILDINGS: Cracked floors, cracked walls, water intrusion, faded paint, vandalism, doors, missing signs, drainage issues
        - COMMS: Emergency telephones, electronic destination signs
        - ELEVATOR AND ESCALATOR: All elevator and escalator related issues (except cleaning — that is System Service)
        - GROUNDS: Landscaping, fencing, maintaining outdoor spaces, grass, trimming, irrigation systems, tree removals
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
        config=GenerateContentConfig(response_logprobs=True, logprobs=3)
    )

    raw_response = (response.text or "").strip()

    if not raw_response:
        raise ValueError("Gemini returned an empty response")

    #converting the log probs to a confidence score
    avg_logprobs = response.candidates[0].avg_logprobs or 0.0
    confidence = math.exp(avg_logprobs)

    return raw_response, confidence

"""
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
        description = getattr(photo, "user_context", "")

        if not file_path or not os.path.exists(file_path):
            print(f"[!] File not found: {file_path}")
            missing_files.append(file_path)
            continue

        raw_response, confidence = identify_objects(
            file_path, 
            DISCIPLINES, 
            user_description=description
        )
        parsed = parse_classification(raw_response)

        photo.vlm_summary = parsed["vlm_summary"]
        db.commit()
        
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
"""

def process_single_photo(photo: PhotoReport, db: Session):
    """Processes a single photo and updates both the Photo and the Parent Incident."""
    file_path = resolve_local_image_path(photo)
    description = getattr(photo, "user_context", "Not provided")
    incident_id = photo.incident_id

    #if no photos exit early
    if not file_path or not os.path.exists(file_path):
        print(f"[!] File not found for photo {photo.evidence_id}: {file_path}")
        photo.photo_report_status = "Error: File Missing"   # type: ignore[assignment]
        db.commit()
        return None

    #Lock the photo_report
    photo.photo_report_status = "In-Progress"       # type: ignore[assignment]
    db.commit()
    print(f"[*] Photo {photo.evidence_id} (Incident {incident_id}) locked as In-Progress")

    try:
        # call identify_object for this photo_report
        raw_response, confidence = identify_objects(
            file_path, 
            DISCIPLINES, 
            user_description=description
        )
        parsed = parse_classification(raw_response)
        discipline = parsed["discipline"] #need to extract this so we can sort by discpline for grouping

        print(f"[*] Generating multimodal embedding for {photo.evidence_id}...")
        vector = generate_embedding(
            text=description, 
            image_paths=[Path(file_path)]
        )

        # 4, GROUPING LOGIC
        incident_match_id, match_score = find_matching_incident(
            db, 
            new_embedding=vector, 
            discipline=discipline
        )
        if incident_match_id:
            # 1. Store the ID of the 'hardcoded' empty incident created by main.py
            original_incident_id = photo.incident_id 
            
            print(f"  [+] Match found! Moving photo to Incident {incident_match_id}")
            
            # 2. Re-assign the photo to the existing incident
            photo.incident_id = incident_match_id
            db.commit() # Commit the move first

            # 3. CLEANUP: Delete the original incident IF it is now empty
            # This prevents 'ghost' incidents from showing up on your dashboard.
            db.execute(
                text("""
                    DELETE FROM incidents 
                    WHERE incident_id = :old_id 
                    AND NOT EXISTS (SELECT 1 FROM photo_reports WHERE incident_id = :old_id)
                """),
                {"old_id": original_incident_id}
            )
            db.commit()

            
        else:
            print("  [-] No match. Keeping photo in its original Incident.")


        # 4. Update the PhotoReport specific fields
        photo.vlm_summary = parsed["vlm_summary"]
        photo.photo_report_discipline = parsed["discipline"]
        photo.embedding = vector
        photo.found_priority = parsed["issue_priority"]
        photo.photo_report_status = "Completed"     # type: ignore[assignment]
        photo.photo_report_confidence = confidence  # type: ignore[assignment]
        
        db.commit()
        print(f"  [+] Photo Result: {parsed['discipline']} (confidence: {confidence:.2f})")

        # 5. Aggregate to the Incident level
        # We fetch the parent incident to update its global state
        incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
        if incident:
            # Check if this new photo is more 'confident' than the current incident data
            # Or if the incident hasn't been set yet
            if incident.discipline is None or confidence > getattr(incident, 'best_confidence', -1.0):
                incident.discipline = parsed["discipline"]
                incident.vlm_summary = parsed["vlm_summary"]
                incident.issue_priority = parsed["issue_priority"]
                #incident.status = "Completed" #this was accidentally marking the entire incident as completed, as in, the engineers have fixed the incident already
                # We store confidence on a temp attribute to help with the next photo comparison
                setattr(incident, 'best_confidence', confidence) 
                
                db.commit()
                print(f"  [✓] Updated Incident {incident_id} -> {parsed['discipline']} | {parsed['issue_priority']}")

        return parsed | {"confidence": confidence}

    except Exception as e:
        print(f"[!] Error processing photo {photo.evidence_id}: {e}")
        photo.photo_report_status = "Error: Inference Failed"       # type: ignore[assignment]
        db.commit()
        return None
    

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
            photo = db.query(PhotoReport).filter(PhotoReport.photo_report_status == "New").first()

            if photo:
                print(f"[*] Processing Photo: {photo.evidence_id}")
                process_single_photo(photo, db)
                print(f"[*] Processed Photo: {photo.evidence_id}")
                
                #if result:
                    # Optional: Update the parent Incident based on this new info
                    #update_parent_incident(photo.incident_id, db)
                
            else:
                print("[~] No new photos. Waiting...")

        # ... error handling ...
        finally:
            db.close()
        time.sleep(10)



if __name__ == "__main__":
    run_processor()
