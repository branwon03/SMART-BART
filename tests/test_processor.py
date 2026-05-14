import json
import src.backend.processor as processor
from src.backend.processor import process_submission, run_processor
from unittest.mock import MagicMock, patch 
from src.backend.database import Incident, PhotoReport

# 1. Setup global mocks
FAKE_RESPONSE = json.dumps({
    "discipline": "MECHANICAL",
    "issue_priority": "HIGH",
    "vlm_summary": "Broken pipe."
})

processor.identify_objects = lambda *args, **kwargs: (FAKE_RESPONSE, 0.95)
processor.generate_embedding = lambda *args, **kwargs: [0.1] * 3072

def make_photo(evidence_id="IMG-001", image_url=None, incident_id="INC-123", submission_id="SUB-001"):
    """Helper to create a mock PhotoReport object"""
    photo = MagicMock()
    photo.evidence_id = evidence_id
    #if no url is provided, use the evidence id so mocks can distinguish them
    photo.image_url = image_url or f"{evidence_id}.jpg"
    photo.incident_id = incident_id
    photo.submission_id = submission_id
    photo.photo_report_status = "New"
    # Ensure these start as None so we can track updates
    photo.photo_report_discipline = None
    photo.found_priority = None
    photo.photo_report_confidence = None 
    return photo

def make_db(photos=None, confidence=None):
    db = MagicMock()
    
    mock_incident = MagicMock()
    mock_incident.discipline = None
    mock_incident.issue_priority = None
    mock_incident.vlm_summary = None

    if photos is None:
        photos = []

    def query_side_effect(model, *args):  
        if model is Incident:
            q = MagicMock()
            q.filter.return_value.first.return_value = mock_incident
            return q
        
        if model is PhotoReport:
            q = MagicMock()
            q.filter.return_value.filter.return_value\
                .with_for_update.return_value.all.return_value = photos
            return q
    
        q = MagicMock()
        q.filter.return_value.filter.return_value.scalar.return_value = confidence
        return q

    db.query.side_effect = query_side_effect
    return db, mock_incident

# Tests:

def test_photo_processing_success():
    """Verify that a photo is correctly updated after a successful run."""
    photo = make_photo()
    db, _ = make_db(photos=[photo])

    with patch("src.backend.processor.find_matching_incident", return_value=(None, 0.0)), \
         patch("os.path.exists", return_value=True):
        process_submission("SUB-001", db)

    # Assertions
    assert photo.photo_report_status == "Completed"
    # We check photo_report_discipline because that is what you named it in database.py
    assert photo.photo_report_discipline == "MECHANICAL"
    assert photo.found_priority == "HIGH"
    assert db.commit.called

def test_photo_processing_file_missing():
    """Verify that the status is set to Error if the image file is missing."""
    photo = make_photo()
    db, _ = make_db(photos=[photo])

    with patch("os.path.exists", return_value=False):
        process_submission("SUB-001", db)

    assert photo.photo_report_status == "Error: File Missing"
    assert db.commit.called

def test_photo_processing_inference_failure():
    """Verify error handling if the model call fails."""
    photo = make_photo()
    db, _ = make_db(photos=[photo])

    with patch("os.path.exists", return_value=True), \
         patch("src.backend.processor.identify_objects", side_effect=Exception("Model Timeout")):
        process_submission("SUB-001", db)

    assert photo.photo_report_status == "Error: Inference Failed"
    assert db.commit.called


# ---------------------------------------------------------------------------
# Multi-photo submission tests  (the new behaviour)
# ---------------------------------------------------------------------------

def test_all_photos_in_submission_assigned_to_same_incident():
    """
    Both photos in a submission must end up in the same incident even when
    only one of them would have passed the similarity threshold on its own.
    The best-confidence photo drives the incident lookup; the weaker photo
    is assigned to the same result.
    """
    strong = make_photo(evidence_id="IMG-STRONG", incident_id="INC-PH-1", submission_id="SUB-002")
    weak   = make_photo(evidence_id="IMG-WEAK",   incident_id="INC-PH-2", submission_id="SUB-002")
    db, _ = make_db(photos=[strong, weak])

    # Simulate: strong photo matches an existing incident, weak one would not
    # (but that decision is made at submission level, so both should be moved)
    with patch("src.backend.processor.find_matching_incident", return_value=("INC-EXISTING", 0.91)), \
         patch("src.backend.processor.identify_objects", return_value=(FAKE_RESPONSE, 0.95)), \
         patch("src.backend.processor.generate_embedding", return_value=[0.1] * 3072), \
         patch("os.path.exists", return_value=True):
        process_submission("SUB-002", db)

    assert strong.incident_id == "INC-EXISTING"
    assert weak.incident_id   == "INC-EXISTING"


def test_submission_uses_best_confidence_photo_for_matching():
    """
    find_matching_incident should be called exactly once per submission,
    using the embedding of the highest-confidence photo.
    """
    low_conf_photo  = make_photo(evidence_id="IMG-LOW",  submission_id="SUB-003")
    high_conf_photo = make_photo(evidence_id="IMG-HIGH", submission_id="SUB-003")

    db, _ = make_db(photos=[low_conf_photo, high_conf_photo])

    HIGH_VECTOR = [0.9] * 3072
    LOW_VECTOR  = [0.1] * 3072

    def fake_embedding(text, image_paths):
        # Return a distinct vector per photo so we can assert which one was used
        if "IMG-HIGH" in str(image_paths):
            return HIGH_VECTOR
        return LOW_VECTOR

    def fake_identify(file_path, *args, **kwargs):
        # Give different confidences based on the path
        if "IMG-HIGH" in file_path:
            return (FAKE_RESPONSE, 0.95)
        return (FAKE_RESPONSE, 0.60)

    with patch("src.backend.processor.find_matching_incident", return_value=(None, 0.0)) as mock_find, \
         patch("src.backend.processor.identify_objects", side_effect=fake_identify), \
         patch("src.backend.processor.generate_embedding", side_effect=fake_embedding), \
         patch("os.path.exists", return_value=True):
        process_submission("SUB-003", db)

    # Must be called exactly once (not once per photo)
    assert mock_find.call_count == 1
    # The vector passed must be the high-confidence photo's vector
    assert mock_find.call_args.kwargs["new_embedding"] == HIGH_VECTOR


def test_one_bad_photo_does_not_block_rest_of_submission():
    """
    If one photo in a submission fails classification, the other should still
    reach Completed and the submission should still attempt incident matching.
    """
    good = make_photo(evidence_id="IMG-GOOD", submission_id="SUB-004")
    bad  = make_photo(evidence_id="IMG-BAD",  submission_id="SUB-004")
    db, _ = make_db(photos=[bad, good])

    def fake_identify(file_path, *args, **kwargs):
        if "IMG-BAD" in file_path:
            raise Exception("GPU OOM")
        return (FAKE_RESPONSE, 0.95)

    with patch("src.backend.processor.find_matching_incident", return_value=(None, 0.0)), \
         patch("src.backend.processor.identify_objects", side_effect=fake_identify), \
         patch("src.backend.processor.generate_embedding", return_value=[0.1] * 3072), \
         patch("os.path.exists", return_value=True):
        process_submission("SUB-004", db)

    assert bad.photo_report_status  == "Error: Inference Failed"
    assert good.photo_report_status == "Completed"


# ---------------------------------------------------------------------------
# Confidence & incident promotion tests
# ---------------------------------------------------------------------------

def test_incident_updated_with_higher_confidence():
    """Incident metadata should be promoted when the new photo has higher confidence."""
    photo = make_photo()
    db, mock_incident = make_db(photos=[photo], confidence=0.80)
    mock_incident.discipline = "ELECTRICAL"

    with patch("src.backend.processor.find_matching_incident", return_value=(None, 0.0)), \
         patch("src.backend.processor.identify_objects", return_value=(FAKE_RESPONSE, 0.95)), \
         patch("src.backend.processor.generate_embedding", return_value=[0.1] * 3072), \
         patch("os.path.exists", return_value=True):
        process_submission("SUB-001", db)

    assert mock_incident.discipline  == "MECHANICAL"
    assert mock_incident.issue_priority == "HIGH"
    assert mock_incident.vlm_summary == "Broken pipe."
    assert db.commit.called


def test_incident_not_updated_with_lower_confidence():
    """Incident metadata should NOT be overwritten by a lower-confidence photo."""
    photo = make_photo()
    db, mock_incident = make_db(photos=[photo], confidence=0.99)
    mock_incident.discipline  = "ELECTRICAL"
    mock_incident.issue_priority = "LOW"

    with patch("src.backend.processor.find_matching_incident", return_value=(None, 0.0)), \
         patch("src.backend.processor.identify_objects", return_value=(FAKE_RESPONSE, 0.95)), \
         patch("src.backend.processor.generate_embedding", return_value=[0.1] * 3072), \
         patch("os.path.exists", return_value=True):
        process_submission("SUB-001", db)

    assert mock_incident.discipline  == "ELECTRICAL"
    assert mock_incident.issue_priority == "LOW"
    assert db.commit.called


def test_photo_reassigned_when_grouping_match_found():
    """All photos should be moved to the matched incident; original placeholder deleted."""
    photo = make_photo(incident_id="INC-OLD")
    db, _ = make_db(photos=[photo])

    with patch("src.backend.processor.find_matching_incident", return_value=("INC-NEW", 0.92)), \
         patch("src.backend.processor.identify_objects", return_value=(FAKE_RESPONSE, 0.95)), \
         patch("src.backend.processor.generate_embedding", return_value=[0.1] * 3072), \
         patch("os.path.exists", return_value=True):
        process_submission("SUB-001", db)

    assert photo.incident_id == "INC-NEW"
    call_args = db.execute.call_args[0][1]
    assert call_args["old_id"] == "INC-OLD"
    assert db.commit.called


# ---------------------------------------------------------------------------
# run_processor / polling tests
# ---------------------------------------------------------------------------

def _make_polling_db(submission_ids):
    """
    Build a mock DB for run_processor tests.
    The processor now queries distinct submission_ids, not photos directly.
    Returns tuples because SQLAlchemy .all() on a column query gives Row tuples.
    """
    db = MagicMock()
    call_count = 0

    def query_side_effect(*args, **kwargs):
        nonlocal call_count
        q = MagicMock()
        if call_count == 0 and submission_ids:
            # First loop: return pending submission_ids as Row-like tuples
            q.filter.return_value.distinct.return_value\
                .limit.return_value.all.return_value = [(sid,) for sid in submission_ids]
        else:
            q.filter.return_value.distinct.return_value\
                .limit.return_value.all.return_value = []
        call_count += 1
        return q

    db.query.side_effect = query_side_effect
    return db


def test_batch_respects_batch_size():
    """The distinct submission_id query must be limited to BATCH_SIZE."""
    db = _make_polling_db(["SUB-001"])

    class StopTest(BaseException):
        pass

    captured_q = {}
    original_side_effect = db.query.side_effect
    call_count = 0

    def capturing_query(*args, **kwargs):
        nonlocal call_count
        q = original_side_effect(*args, **kwargs)
        if call_count == 0:
            captured_q["first"] = q
        call_count += 1
        return q

    db.query.side_effect = capturing_query

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.process_submission"), \
         patch("src.backend.processor.engine") as mock_engine, \
         patch("src.backend.processor.time") as mock_time:
        mock_time.sleep.side_effect = StopTest
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        try:
            run_processor()
        except StopTest:
            pass

    limit_call = captured_q["first"].filter.return_value\
        .distinct.return_value.limit.call_args
    assert limit_call is not None
    assert limit_call[0][0] == processor.BATCH_SIZE


def test_no_sleep_when_photos_available():
    """time.sleep should NOT be called on the iteration that processes submissions."""
    db = _make_polling_db(["SUB-001"])

    class StopTest(BaseException):
        pass

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.process_submission"), \
         patch("src.backend.processor.engine") as mock_engine, \
         patch("src.backend.processor.time") as mock_time:
        mock_time.sleep.side_effect = StopTest
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        try:
            run_processor()
        except StopTest:
            pass

    # Sleep only fires on the second (empty) loop
    assert mock_time.sleep.call_count == 1
    assert mock_time.sleep.call_args[0][0] == 10


def test_sleep_when_queue_empty():
    """time.sleep(10) must be called when no pending submissions exist."""
    db = _make_polling_db([])

    class StopTest(BaseException):
        pass

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.engine") as mock_engine, \
         patch("src.backend.processor.time") as mock_time:
        mock_time.sleep.side_effect = StopTest
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        try:
            run_processor()
        except StopTest:
            pass

    assert mock_time.sleep.call_count == 1
    assert mock_time.sleep.call_args[0][0] == 10


def test_error_in_one_submission_does_not_stop_batch():
    """A failure in one submission should not prevent others from being processed."""
    db = _make_polling_db(["SUB-BAD", "SUB-GOOD"])
    processed = []

    def fake_process(submission_id, db):
        if submission_id == "SUB-BAD":
            raise Exception("Exploded")
        processed.append(submission_id)

    class StopTest(BaseException):
        pass

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.process_submission", side_effect=fake_process), \
         patch("src.backend.processor.engine") as mock_engine, \
         patch("src.backend.processor.time") as mock_time:
        mock_time.sleep.side_effect = lambda s: (_ for _ in ()).throw(StopTest) if s == 10 else None
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        try:
            run_processor()
        except StopTest:
            pass

    assert "SUB-GOOD" in processed


def test_in_progress_photos_not_picked_up():
    """Submissions with all photos In-Progress should not appear (skip_locked)."""
    db = _make_polling_db([])  # skip_locked means the row isn't visible → empty result

    class StopTest(BaseException):
        pass

    with patch("src.backend.processor.SessionLocal", side_effect=lambda: db), \
         patch("src.backend.processor.process_submission") as mock_process, \
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
    """A DB error should trigger a 5-second sleep before the next retry."""
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