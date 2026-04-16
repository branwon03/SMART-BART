import src.backend.processor as processor
from src.backend.processor import process_single_photo, run_processor
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

# Tests:

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

# confidence and grouping tests:

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

# polling tests:

def test_batch_respects_batch_size():
    """Verify that the query is limited to BATCH_SIZE photos per loop."""
    photo = make_photo()
    db = MagicMock()
    captured_q = {}  # capture the actual mock returned by query_side_effect

    call_count = 0
    def query_side_effect(*args, **kwargs):
        nonlocal call_count
        q = MagicMock()
        if call_count == 0:
            q.filter.return_value.with_for_update.return_value.limit.return_value.all.return_value = [photo]
            captured_q["first"] = q  # save reference to check later
        else:
            q.filter.return_value.with_for_update.return_value.limit.return_value.all.return_value = []
        call_count += 1
        return q

    db.query.side_effect = query_side_effect

    class StopTest(BaseException):
        pass

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.process_single_photo"), \
         patch("src.backend.processor.engine") as mock_engine, \
         patch("src.backend.processor.time") as mock_time:
        mock_time.sleep.side_effect = StopTest
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        try:
            run_processor()
        except StopTest:
            pass

    # Use the captured q instead of db.query.return_value
    limit_call = captured_q["first"].filter.return_value\
        .with_for_update.return_value.limit.call_args
    assert limit_call is not None
    assert limit_call[0][0] == processor.BATCH_SIZE

def test_no_sleep_when_photos_available():
    """Verify time.sleep is NOT called when there are photos to process."""
    photo = make_photo()
    db = MagicMock()
    call_count = 0

    def query_side_effect(*args, **kwargs):
        nonlocal call_count
        q = MagicMock()
        if call_count == 0:
            q.filter.return_value.with_for_update.return_value.limit.return_value.all.return_value = [photo]
        else:
            q.filter.return_value.with_for_update.return_value.limit.return_value.all.return_value = []
        call_count += 1
        return q

    db.query.side_effect = query_side_effect

    class StopTest(BaseException):
        pass

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.process_single_photo"), \
         patch("src.backend.processor.engine") as mock_engine, \
         patch("src.backend.processor.time") as mock_time:
        mock_time.sleep.side_effect = StopTest  # BaseException bypasses except Exception
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        try:
            run_processor()
        except StopTest:
            pass

    # Sleep should only have been called once — on the second loop when queue was empty
    assert mock_time.sleep.call_count == 1
    assert mock_time.sleep.call_args[0][0] == 10

def test_sleep_when_queue_empty():
    """Verify time.sleep(10) is called when no photos are in the queue."""
    db = MagicMock()
    db.query.return_value.filter.return_value\
        .with_for_update.return_value.limit.return_value.all.return_value = []
    
    class StopTest(BaseException):
        pass

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.engine") as mock_engine, \
         patch("src.backend.processor.time") as mock_time:  # patch the whole time module
        mock_time.sleep.side_effect = StopTest
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        try:
            run_processor()
        except StopTest:
            pass

    assert mock_time.sleep.call_count == 1
    assert mock_time.sleep.call_args[0][0] == 10


def test_error_in_one_photo_does_not_stop_batch():
    """If one photo fails, the rest of the batch should still be processed."""
    good_photo = make_photo(evidence_id="IMG-GOOD")
    bad_photo = make_photo(evidence_id="IMG-BAD")
    db = MagicMock()
    call_count = 0

    def query_side_effect(*args, **kwargs):
        nonlocal call_count
        q = MagicMock()
        if call_count == 0:
            q.filter.return_value.with_for_update.return_value.limit.return_value.all.return_value = [bad_photo, good_photo]
        else:
            q.filter.return_value.with_for_update.return_value.limit.return_value.all.return_value = []
        call_count += 1
        return q

    db.query.side_effect = query_side_effect
    processed = []

    def fake_process(photo, db):
        if photo.evidence_id == "IMG-BAD":
            raise Exception("Inference exploded")
        processed.append(photo.evidence_id)

    class StopTest(BaseException):
        pass

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.process_single_photo", side_effect=fake_process), \
         patch("src.backend.processor.engine") as mock_engine, \
         patch("src.backend.processor.time") as mock_time:
        mock_time.sleep.side_effect = lambda s: (_ for _ in ()).throw(StopTest) if s == 10 else None
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        try:
            run_processor()
        except StopTest:
            pass

    assert "IMG-GOOD" in processed

def test_in_progress_photos_not_picked_up():
    """Photos already marked In-Progress should not appear in the batch (skip_locked)."""
    db = MagicMock()

    # Simulate skip_locked by returning empty (locked row not visible)
    db.query.return_value.filter.return_value\
        .with_for_update.return_value.limit.return_value.all.return_value = []
    
    class StopTest(BaseException):
        pass

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.process_single_photo") as mock_process, \
         patch("src.backend.processor.engine") as mock_engine, \
         patch("src.backend.processor.time") as mock_time:
        mock_time.sleep.side_effect = StopTest
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        try:
            run_processor()
        except StopTest:
            pass

    assert not mock_process.called


def test_db_error_triggers_retry_sleep():
    """A DB connection error should trigger a 5 second sleep before retrying."""
    db = MagicMock()
    db.query.side_effect = Exception("DB connection lost")

    class StopTest(BaseException):
        pass

    sleep_calls = []
    def track_sleep(seconds):
        sleep_calls.append(seconds)
        if len(sleep_calls) >= 1:
            raise StopTest

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.engine") as mock_engine, \
         patch("src.backend.processor.time") as mock_time:
        mock_time.sleep.side_effect = track_sleep
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        try:
            run_processor()
        except StopTest:
            pass

    assert sleep_calls == [5]