from datetime import datetime

import src.backend.grouping as grouping
from src.backend.grouping import find_matching_incident


def test_find_matching_incident_returns_none_none_when_embedding_missing():
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
    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="UNCLASSIFIED",
        location_id="station_1",
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
    )
    assert incident_id is None
    assert score is None


def test_find_matching_incident_returns_none_none_when_location_missing():
    incident_id, score = find_matching_incident(
        db=object(),
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        location_id=None,
        submitted_at=datetime(2026, 4, 20, 12, 0, 0),
    )
    assert incident_id is None
    assert score is None


def test_find_matching_incident_returns_none_none_when_submitted_at_missing():
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
    def fake_best_match(db, new_embedding, discipline, location_id, submitted_at, time_window_hours):
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
    def fake_best_match(db, new_embedding, discipline, location_id, submitted_at, time_window_hours):
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
    def fake_best_match(db, new_embedding, discipline, location_id, submitted_at, time_window_hours):
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