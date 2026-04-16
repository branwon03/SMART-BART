import src.backend.processor as processor
from src.backend.processor import process_single_photo
from unittest.mock import MagicMock, patch
from src.backend.database import Incident

# 1. Setup global mocks
FAKE_RESPONSE = (
    "discipline: MECHANICAL\n"
    "issue_priority: HIGH\n"
    "vlm_summary: Broken pipe."
)

processor.identify_objects = lambda *args, **kwargs: (FAKE_RESPONSE, 0.95)
processor.generate_embedding = lambda *args, **kwargs: [0.1] * 3072

def make_photo(evidence_id="IMG-001", image_url="test.jpg", incident_id="INC-123"):
    """Helper to create a mock PhotoReport object"""
    photo = MagicMock()
    photo.evidence_id = evidence_id
    photo.image_url = image_url
    photo.incident_id = incident_id
    photo.photo_report_status = "New"
    # Ensure these start as None so we can track updates
    photo.photo_report_discipline = None
    photo.found_priority = None
    return photo

def make_db(confidence=None):
    db = MagicMock()
    
    mock_incident = MagicMock()
    mock_incident.discipline = None
    mock_incident.issue_priority = None
    mock_incident.vlm_summary = None

    def query_side_effect(model, *args):  
        if model is Incident:
            q = MagicMock()
            q.filter.return_value.first.return_value = mock_incident
            return q
        q = MagicMock()
        q.filter.return_value.filter.return_value.scalar.return_value = confidence
        q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = query_side_effect
    return db, mock_incident

def test_photo_processing_success():
    """Verify that a photo is correctly updated after a successful run."""
    photo = make_photo()
    db, _ = make_db()

    with patch("src.backend.processor.find_matching_incident", return_value=(None, 0.0)), \
         patch("os.path.exists", return_value=True):
        process_single_photo(photo, db)

    # Assertions
    assert photo.photo_report_status == "Completed"
    # We check photo_report_discipline because that is what you named it in database.py
    assert photo.photo_report_discipline == "MECHANICAL"
    assert photo.found_priority == "HIGH"
    assert db.commit.called

def test_photo_processing_file_missing():
    """Verify that the status is set to Error if the image file is missing."""
    photo = make_photo()
    db, _ = make_db()

    with patch("os.path.exists", return_value=False):
        process_single_photo(photo, db)

    assert photo.photo_report_status == "Error: File Missing"
    assert db.commit.called

def test_photo_processing_inference_failure():
    """Verify error handling if the model call fails."""
    photo = make_photo()
    db, _ = make_db()

    with patch("os.path.exists", return_value=True), \
         patch("src.backend.processor.identify_objects", side_effect=Exception("Model Timeout")):
        
        process_single_photo(photo, db)

    assert photo.photo_report_status == "Error: Inference Failed"
    assert db.commit.called

def test_incident_updated_with_higher_confidence():
    """Incident metadata should be promoted when the new photo has higher confidence."""
    photo = make_photo()
    db, mock_incident = make_db(confidence=0.80)
    mock_incident.discipline = "ELECTRICAL"

    with patch("src.backend.processor.find_matching_incident", return_value=(None, 0.0)), \
         patch("src.backend.processor.identify_objects", return_value=(FAKE_RESPONSE, 0.95)), \
         patch("src.backend.processor.generate_embedding", return_value=[0.1] * 3072), \
         patch("os.path.exists", return_value=True):
        process_single_photo(photo, db)

    assert mock_incident.discipline == "MECHANICAL"
    assert mock_incident.issue_priority == "HIGH"
    assert mock_incident.vlm_summary == "Broken pipe."
    assert db.commit.called

def test_incident_not_updated_with_lower_confidence():
    """Incident metadata should NOT be overwritten by a lower-confidence photo."""
    photo = make_photo()
    db, mock_incident = make_db(confidence=0.99)
    mock_incident.discipline = "ELECTRICAL"
    mock_incident.issue_priority = "LOW"

    with patch("src.backend.processor.find_matching_incident", return_value=(None, 0.0)), \
         patch("src.backend.processor.identify_objects", return_value=(FAKE_RESPONSE, 0.95)), \
         patch("src.backend.processor.generate_embedding", return_value=[0.1] * 3072), \
         patch("os.path.exists", return_value=True):
        process_single_photo(photo, db)

    assert mock_incident.discipline == "ELECTRICAL" 
    assert mock_incident.issue_priority == "LOW"
    assert db.commit.called

def test_photo_reassigned_when_grouping_match_found():
    """Photo should be moved to the matched incident and original deleted."""
    photo = make_photo(incident_id="INC-OLD")
    db, _ = make_db()

    with patch("src.backend.processor.find_matching_incident", return_value=("INC-NEW", 0.92)), \
         patch("src.backend.processor.identify_objects", return_value=(FAKE_RESPONSE, 0.95)), \
         patch("src.backend.processor.generate_embedding", return_value=[0.1] * 3072), \
         patch("os.path.exists", return_value=True):
        process_single_photo(photo, db)

    assert photo.incident_id == "INC-NEW"
    # Verify the DELETE used the correct original incident ID
    call_args = db.execute.call_args[0][1]
    assert call_args["old_id"] == "INC-OLD"
    assert db.commit.called