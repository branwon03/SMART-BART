import src.backend.processor as processor
from src.backend.processor import process_single_photo
from unittest.mock import MagicMock, patch

# Global Mock Response
FAKE_RESPONSE = "discipline: MECHANICAL\nissue_priority: HIGH\nvlm_summary: Placeholder summary."

def make_incident():
    # We use a real object-like mock here
    incident = MagicMock()
    incident.incident_id = "TEST-001"
    incident.discipline = None
    return incident

def make_photo():
    photo = MagicMock()
    photo.incident_id = "TEST-001"
    photo.evidence_id = "IMG-001"
    photo.photo_report_status = "New"
    return photo

def make_db(photo, incident):
    db = MagicMock()
    # The nesting must match exactly how your code calls it:
    # db.query(Incident).filter(Incident.incident_id == ...).first()
    db.query.return_value.filter.return_value.first.return_value = incident
    return db

# --- THE TESTS ---

def test_single_photo_happy_path():
    incident = make_incident()
    photo = make_photo()
    db = make_db(photo, incident)
    
    # We patch BOTH the resolver AND the os.path check
    with patch("src.backend.processor.resolve_local_image_path", return_value="dummy.jpg"), \
         patch("os.path.exists", return_value=True), \
         patch("src.backend.processor.generate_embedding", return_value=[0.1]*3072), \
         patch("src.backend.processor.find_matching_incident", return_value=(None, 0.0)), \
         patch.object(processor, "identify_objects", return_value=(FAKE_RESPONSE, 0.95)):
        
        process_single_photo(photo, db)

    
    assert incident.discipline == "MECHANICAL"

def test_all_files_missing_sets_error_status():
    incident = make_incident()
    photo = make_photo()
    db = make_db(photo, incident)

    
    with patch("src.backend.processor.resolve_local_image_path", return_value="missing.jpg"), \
         patch("os.path.exists", return_value=False):
        
        process_single_photo(photo, db)

    assert photo.photo_report_status == "Error: File Missing"