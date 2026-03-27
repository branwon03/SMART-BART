import os
import time
from sqlalchemy.orm import Session
from src.backend.database import SessionLocal, Incident, PhotoReport
from src.backend.gemini_parser import parse_classification, DISCIPLINES
 
UPLOAD_DIR = os.path.join("src", "backend", "uploads")

def identify_objects(image_path: str, class_list: list) -> tuple[str, float]:
    """
    TODO: Replace placeholder with real Gemini model logic:
      1. Load / initialize the model
      2. Encode the image
      3. Run inference and prompt Gemini to return:
            discipline: <value>
            issue_priority: <value>
            vlm_summary: <value>
      4. Return the raw response string and a confidence score
    """
    print(f"  [model] Running inference on {os.path.basename(image_path)}")
 
    #Placeholder — simulates a Gemini response string
    raw_response = (
        "discipline: MECHANICAL\n"
        "issue_priority: HIGH\n"
        "vlm_summary: Placeholder summary of identified issue."
    )
    confidence = 0.91
 
    return raw_response, confidence

#kiara's parsing logic, clean raw model output and map to bart labels

def process_incident(incident: Incident, db: Session):
    #runs the full pipeline for a single incident: selection -> lock -> model loop -> parse -> map -> save 

    incident_id = incident.incident_id

    incident.status = "In-Progress"       # type: ignore[assignment]
    db.commit()
    print(f"[*] Incident {incident_id} locked as In-Progress")

    photos = db.query(PhotoReport).filter(PhotoReport.incident_id == incident_id).all()

    #if no photos exit early 
    if not photos:
        print(f"[!] No photos found for incident {incident_id}")
        incident.status = "Error: No Photos"       # type: ignore[assignment]
        db.commit()
        return 
    
    best_category = None 
    best_summary = None
    best_confidence = -1.0
    missing_files = []

    for photo in photos:
        file_path = os.path.join(UPLOAD_DIR, photo.image_url)

        if not os.path.exists(file_path):
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
        incident.status = "Error: All Files Missing"        # type: ignore[assignment]
        print(f"[!] All files missing for incident {incident_id}")

    elif best_category is None:
        incident.status = "Error: Model Returned No Results" # type: ignore[assignment]
        print(f"[!] Model returned no results for incident {incident_id}")

    else:
        incident.discipline = best_category      # type: ignore[assignment]
        incident.vlm_summary = best_summary      # type: ignore[assignment]
        incident.issue_priority = best_priority  # type: ignore[assignment]
        incident.status = "Completed"            # type: ignore[assignment]
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
