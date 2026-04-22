from datetime import datetime
from types import SimpleNamespace

import src.backend.grouping as grouping
from src.backend.grouping import (
    _cosine_similarity_fallback,
    _get_best_match_sqlite,
    find_matching_incident,
)


# Main Postgres-path tests

def test_find_matching_incident_returns_none_none_when_embedding_missing():
    # If there is no embedding, grouping cannot run at all.
    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=None,
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
    )
    assert incident_id is None
    assert score is None


def test_find_matching_incident_skips_unclassified_reports():
    # If the discipline is too weak / unknown, skip grouping.
    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="UNCLASSIFIED",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
    )
    assert incident_id is None
    assert score is None


def test_find_matching_incident_allows_fallback_when_location_missing(monkeypatch):
    # Location is preferred, but grouping should still work without it.
    def fake_best_match(
        db,
        new_embedding,
        discipline,
        location_id,
        submitted_at,
        time_window_hours,
        exclude_evidence_id,
    ):
        assert location_id is None
        assert exclude_evidence_id is None
        return (202, 0.0)  # distance 0.0 => similarity 1.0

    monkeypatch.setattr(grouping, "_USE_SQLITE", False)
    monkeypatch.setattr(grouping, "_get_best_match_postgres", fake_best_match)

    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id=None,
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        threshold=0.80,
    )

    assert incident_id == 202
    assert score == 1.0


def test_find_matching_incident_returns_none_none_when_submitted_at_missing():
    # We need a timestamp so the time-window filter can work.
    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=None,
    )
    assert incident_id is None
    assert score is None


def test_find_matching_incident_returns_best_match_above_threshold(monkeypatch):
    # If the best match score is strong enough, reuse that incident.
    def fake_best_match(
        db,
        new_embedding,
        discipline,
        location_id,
        submitted_at,
        time_window_hours,
        exclude_evidence_id,
    ):
        assert exclude_evidence_id is None
        return (202, 0.0)  # distance 0.0 => similarity 1.0

    monkeypatch.setattr(grouping, "_USE_SQLITE", False)
    monkeypatch.setattr(grouping, "_get_best_match_postgres", fake_best_match)

    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        threshold=0.80,
    )

    assert incident_id == 202
    assert score == 1.0


def test_find_matching_incident_returns_none_when_best_score_below_threshold(monkeypatch):
    # If the best candidate is below threshold, do not group it.
    def fake_best_match(
        db,
        new_embedding,
        discipline,
        location_id,
        submitted_at,
        time_window_hours,
        exclude_evidence_id,
    ):
        assert exclude_evidence_id is None
        return (22, 0.10)  # distance 0.10 => similarity 0.90

    monkeypatch.setattr(grouping, "_USE_SQLITE", False)
    monkeypatch.setattr(grouping, "_get_best_match_postgres", fake_best_match)

    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        threshold=0.95,
    )

    assert incident_id is None
    assert score == 0.90


def test_find_matching_incident_returns_none_and_negative_one_when_no_candidates(monkeypatch):
    # If there are no usable candidates at all, return no match and -1.0 score.
    def fake_best_match(
        db,
        new_embedding,
        discipline,
        location_id,
        submitted_at,
        time_window_hours,
        exclude_evidence_id,
    ):
        assert exclude_evidence_id is None
        return None

    monkeypatch.setattr(grouping, "_USE_SQLITE", False)
    monkeypatch.setattr(grouping, "_get_best_match_postgres", fake_best_match)

    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        threshold=0.80,
    )

    assert incident_id is None
    assert score == -1.0


def test_find_matching_incident_passes_exclude_evidence_id(monkeypatch):
    # This proves the self-match guard is passed through to the helper.
    def fake_best_match(
        db,
        new_embedding,
        discipline,
        location_id,
        submitted_at,
        time_window_hours,
        exclude_evidence_id,
    ):
        assert exclude_evidence_id == "IMG-123"
        return (202, 0.0)

    monkeypatch.setattr(grouping, "_USE_SQLITE", False)
    monkeypatch.setattr(grouping, "_get_best_match_postgres", fake_best_match)

    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        threshold=0.80,
        exclude_evidence_id="IMG-123",
    )

    assert incident_id == 202
    assert score == 1.0


# SQLite helper test doubles

class FakeSQLiteQuery:
    """
    Tiny fake query object.

    Our real SQLite helper does:
      db.query(...).join(...).filter(...).all()

    So this fake object only needs to support those calls.
    The filters do nothing here because we are only testing the
    helper's scoring / return behavior, not SQLAlchemy itself.
    """

    def __init__(self, candidates):
        self._candidates = candidates

    def join(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._candidates


class FakeSQLiteDB:
    """
    Tiny fake DB that always returns our fake query object.
    """

    def __init__(self, candidates):
        self._candidates = candidates

    def query(self, *args, **kwargs):
        return FakeSQLiteQuery(self._candidates)


# _cosine_similarity_fallback tests

def test_cosine_similarity_fallback_returns_negative_one_when_embedding_missing():
    # Missing vectors cannot be compared.
    assert _cosine_similarity_fallback(None, [1.0, 0.0]) == -1.0
    assert _cosine_similarity_fallback([1.0, 0.0], None) == -1.0


def test_cosine_similarity_fallback_returns_negative_one_when_dimensions_mismatch():
    # Vectors must have the same length.
    assert _cosine_similarity_fallback([1.0, 0.0], [1.0, 0.0, 0.0]) == -1.0


def test_cosine_similarity_fallback_returns_negative_one_for_zero_magnitude_vector():
    # Zero-length magnitude would cause divide-by-zero, so helper returns -1.0.
    assert _cosine_similarity_fallback([0.0, 0.0], [1.0, 0.0]) == -1.0
    assert _cosine_similarity_fallback([1.0, 0.0], [0.0, 0.0]) == -1.0


def test_cosine_similarity_fallback_returns_valid_similarity_for_matching_vectors():
    # Identical vectors should give cosine similarity 1.0.
    score = _cosine_similarity_fallback([1.0, 0.0], [1.0, 0.0])
    assert score == 1.0


def test_cosine_similarity_fallback_returns_zero_for_orthogonal_vectors():
    # Perpendicular vectors should give cosine similarity 0.0.
    score = _cosine_similarity_fallback([1.0, 0.0], [0.0, 1.0])
    assert score == 0.0


# _get_best_match_sqlite tests

def test_get_best_match_sqlite_returns_best_candidate():
    # Candidate 1 is identical to the new embedding, so it should win.
    db = FakeSQLiteDB([
        SimpleNamespace(incident_id="INC-1", embedding=[1.0, 0.0], evidence_id="A"),
        SimpleNamespace(incident_id="INC-2", embedding=[0.0, 1.0], evidence_id="B"),
    ])

    result = _get_best_match_sqlite(
        db=db,
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        time_window_hours=24,
        exclude_evidence_id=None,
    )

    assert result == ("INC-1", 1.0)


def test_get_best_match_sqlite_returns_none_when_no_candidates():
    # No candidates means no match.
    db = FakeSQLiteDB([])

    result = _get_best_match_sqlite(
        db=db,
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        time_window_hours=24,
        exclude_evidence_id=None,
    )

    assert result is None


# Main SQLite-path tests

def test_find_matching_incident_sqlite_returns_best_match_above_threshold(monkeypatch):
    # The SQLite fallback path should also reuse a strong enough match.
    def fake_best_match(
        db,
        new_embedding,
        discipline,
        location_id,
        submitted_at,
        time_window_hours,
        exclude_evidence_id,
    ):
        assert location_id == "station_1"
        assert exclude_evidence_id is None
        return ("INC-SQLITE", 1.0)

    monkeypatch.setattr(grouping, "_USE_SQLITE", True)
    monkeypatch.setattr(grouping, "_get_best_match_sqlite", fake_best_match)

    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        threshold=0.80,
    )

    assert incident_id == "INC-SQLITE"
    assert score == 1.0


def test_find_matching_incident_sqlite_returns_none_when_best_score_below_threshold(monkeypatch):
    # The SQLite fallback path should not group a weak match.
    def fake_best_match(
        db,
        new_embedding,
        discipline,
        location_id,
        submitted_at,
        time_window_hours,
        exclude_evidence_id,
    ):
        assert exclude_evidence_id is None
        return ("INC-SQLITE", 0.70)

    monkeypatch.setattr(grouping, "_USE_SQLITE", True)
    monkeypatch.setattr(grouping, "_get_best_match_sqlite", fake_best_match)

    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        threshold=0.80,
    )

    assert incident_id is None
    assert score == 0.70


def test_find_matching_incident_sqlite_returns_none_and_negative_one_when_no_candidates(monkeypatch):
    # If SQLite finds no candidates, the result should match the Postgres behavior.
    def fake_best_match(
        db,
        new_embedding,
        discipline,
        location_id,
        submitted_at,
        time_window_hours,
        exclude_evidence_id,
    ):
        assert exclude_evidence_id is None
        return None

    monkeypatch.setattr(grouping, "_USE_SQLITE", True)
    monkeypatch.setattr(grouping, "_get_best_match_sqlite", fake_best_match)

    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        threshold=0.80,
    )

    assert incident_id is None
    assert score == -1.0


def test_find_matching_incident_sqlite_passes_exclude_evidence_id(monkeypatch):
    # The self-match guard should also be passed into the SQLite helper.
    def fake_best_match(
        db,
        new_embedding,
        discipline,
        location_id,
        submitted_at,
        time_window_hours,
        exclude_evidence_id,
    ):
        assert exclude_evidence_id == "IMG-SQLITE-123"
        return ("INC-SQLITE", 1.0)

    monkeypatch.setattr(grouping, "_USE_SQLITE", True)
    monkeypatch.setattr(grouping, "_get_best_match_sqlite", fake_best_match)

    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
        threshold=0.80,
        exclude_evidence_id="IMG-SQLITE-123",
    )

    assert incident_id == "INC-SQLITE"
    assert score == 1.0