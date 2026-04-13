import src.backend.processor as processor
from src.backend.processor import process_single_photo
from unittest.mock import MagicMock, patch

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

def make_db():
    """Helper to create a mock database session"""
    db = MagicMock()
    # Mock query chain to return None (no grouping match)
    db.query.return_value.filter.return_value.first.return_value = None
    return db

def test_photo_processing_success():
    """Verify that a photo is correctly updated after a successful run."""
    photo = make_photo()
    db = make_db()

    with patch("os.path.exists", return_value=True):
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
    db = make_db()

    with patch("os.path.exists", return_value=False):
        process_single_photo(photo, db)

    assert photo.photo_report_status == "Error: File Missing"
    assert db.commit.called

def test_photo_processing_inference_failure():
    """Verify error handling if the model call fails."""
    photo = make_photo()
    db = make_db()

    with patch("os.path.exists", return_value=True), \
         patch("src.backend.processor.identify_objects", side_effect=Exception("Model Timeout")):
        
        process_single_photo(photo, db)

    assert photo.photo_report_status == "Error: Inference Failed"
    assert db.commit.called