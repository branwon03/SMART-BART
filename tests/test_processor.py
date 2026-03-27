import pytest
from unittest.mock import MagicMock, patch
import src.backend.processor as processor

#intended to mimic a gemini-style response string 
FAKE_RESPONSE = (
    "discipline: MECHANICAL\n"
    "issue_priority: HIGH\n"
    "vlm_summary: Placeholder summary of identified issue."
)

processor.identify_objects = lambda path, class_list: (FAKE_RESPONSE, 0.91)

from src.backend.processor import process_incident

#helper functions to create fake database objects
def make_incident(incident_id="TEST-001", status="New"):
    incident = MagicMock()
    incident.incident_id = incident_id
    incident.status = status
    return incident


def make_photo(image_url="test_image.jpg"):
    photo = MagicMock()
    photo.image_url = image_url
    return photo


def make_db(photos: list):
    db = MagicMock()
    db.query().filter().all.return_value = photos
    return db

#this locks the incident
def test_incident_locked_as_in_progress():
    """Incident should be committed as In-Progress before model runs."""
    incident = make_incident()
    photo = make_photo()

    with patch("os.path.exists", return_value=True):
        db = make_db([photo])
        process_incident(incident, db)

    assert db.commit.call_count >= 2  #once for lock, once for save


#run the model and parsing 
def test_single_photo_happy_path():
    """One photo, model runs, parsed correctly, incident saved as Completed."""
    incident = make_incident()
    photo = make_photo("photo1.jpg")

    with patch("os.path.exists", return_value=True):
        db = make_db([photo])
        process_incident(incident, db)

    assert incident.status == "Completed"
    assert incident.discipline == "MECHANICAL"
    assert incident.issue_priority == "HIGH"
    assert incident.vlm_summary == "Placeholder summary of identified issue."


def test_multiple_photos_picks_highest_confidence():
    """With multiple photos the highest confidence result wins."""
    incident = make_incident()
    photos = [make_photo("photo1.jpg"), make_photo("photo2.jpg")]

    responses = [
        ("discipline: ELECTRICAL\nissue_priority: LOW\nvlm_summary: Low confidence result.", 0.55),
        ("discipline: MECHANICAL\nissue_priority: HIGH\nvlm_summary: High confidence result.", 0.95),
    ]

    with patch("os.path.exists", return_value=True), \
         patch.object(processor, "identify_objects", side_effect=responses):

        db = make_db(photos)
        process_incident(incident, db)

    assert incident.status == "Completed"
    assert incident.discipline == "MECHANICAL"
    assert incident.vlm_summary == "High confidence result."


def test_missing_file_is_skipped():
    """Missing photo is skipped, processing continues on remaining photos."""
    incident = make_incident()
    photos = [make_photo("missing.jpg"), make_photo("exists.jpg")]

    with patch("os.path.exists", side_effect=lambda p: "missing" not in p):
        db = make_db(photos)
        process_incident(incident, db)

    assert incident.status == "Completed"
    assert incident.discipline == "MECHANICAL"


#error cases
def test_no_photos_sets_error_status():
    """No photos attached → Error: No Photos."""
    incident = make_incident()
    db = make_db([])

    process_incident(incident, db)

    assert incident.status == "Error: No Photos"


def test_all_files_missing_sets_error_status():
    """All photo files missing on disk → Error: All Files Missing."""
    incident = make_incident()
    photos = [make_photo("missing1.jpg"), make_photo("missing2.jpg")]

    with patch("os.path.exists", return_value=False):
        db = make_db(photos)
        process_incident(incident, db)

    assert incident.status == "Error: All Files Missing"


def test_model_returns_no_discipline_sets_error():
    """If parser can't extract a discipline → Error: Model Returned No Results."""
    incident = make_incident()
    photo = make_photo("photo.jpg")

    bad_response = "issue_priority: HIGH\nvlm_summary: Something happened."  # no discipline field

    with patch("os.path.exists", return_value=True), \
         patch.object(processor, "identify_objects", return_value=(bad_response, 0.91)):

        db = make_db([photo])
        process_incident(incident, db)

    assert incident.status == "Error: Model Returned No Results"


def test_db_committed_at_least_twice():
    """DB should commit on lock and again on final save."""
    incident = make_incident()
    photo = make_photo()

    with patch("os.path.exists", return_value=True):
        db = make_db([photo])
        process_incident(incident, db)

    assert db.commit.call_count >= 2