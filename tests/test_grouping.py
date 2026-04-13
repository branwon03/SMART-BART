import pytest

from src.backend.grouping import cosine_similarity, find_matching_incident


class FakePhoto:
    def __init__(self, incident_id, embedding):
        self.incident_id = incident_id
        self.embedding = embedding


class FakeQuery:
    def __init__(self, candidates):
        self._candidates = candidates

    def filter(self, *args, **kwargs):
        # We do not need to evaluate SQLAlchemy filter expressions here.
        # These tests focus on grouping decision logic once candidates exist.
        return self

    def all(self):
        return self._candidates


class FakeDB:
    def __init__(self, candidates):
        self._candidates = candidates

    def query(self, *args, **kwargs):
        return FakeQuery(self._candidates)


def test_cosine_similarity_identical_vectors():
    score = cosine_similarity([1, 2, 3], [1, 2, 3])
    assert score == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    score = cosine_similarity([1, 0], [0, 1])
    assert score == pytest.approx(0.0)


def test_cosine_similarity_returns_negative_one_when_vector_missing():
    assert cosine_similarity(None, [1, 2, 3]) == -1.0
    assert cosine_similarity([1, 2, 3], None) == -1.0


def test_cosine_similarity_returns_negative_one_when_dimensions_do_not_match():
    assert cosine_similarity([1, 2], [1, 2, 3]) == -1.0


def test_cosine_similarity_returns_negative_one_for_zero_magnitude_vector():
    assert cosine_similarity([0, 0, 0], [1, 2, 3]) == -1.0


def test_find_matching_incident_returns_none_none_when_embedding_missing():
    db = FakeDB([])
    incident_id, score = find_matching_incident(
        db=db,
        new_embedding=None,
        discipline="ELECTRICAL",
    )
    assert incident_id is None
    assert score is None


def test_find_matching_incident_skips_unclassified_reports():
    db = FakeDB([])
    incident_id, score = find_matching_incident(
        db=db,
        new_embedding=[1.0, 0.0],
        discipline="UNCLASSIFIED",
    )
    assert incident_id is None
    assert score is None


def test_find_matching_incident_returns_best_match_above_threshold():
    candidates = [
        FakePhoto(incident_id=101, embedding=[0.8, 0.2]),
        FakePhoto(incident_id=202, embedding=[1.0, 0.0]),
        FakePhoto(incident_id=303, embedding=[0.0, 1.0]),
    ]
    db = FakeDB(candidates)

    incident_id, score = find_matching_incident(
        db=db,
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        threshold=0.80,
    )

    assert incident_id == 202
    assert score == pytest.approx(1.0)


def test_find_matching_incident_returns_none_when_best_score_below_threshold():
    candidates = [
        FakePhoto(incident_id=11, embedding=[0.0, 1.0]),
        FakePhoto(incident_id=22, embedding=[0.6, 0.8]),
    ]
    db = FakeDB(candidates)

    incident_id, score = find_matching_incident(
        db=db,
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        threshold=0.95,
    )

    assert incident_id is None
    assert score < 0.95


def test_find_matching_incident_returns_none_and_negative_one_when_no_candidates():
    db = FakeDB([])

    incident_id, score = find_matching_incident(
        db=db,
        new_embedding=[1.0, 0.0],
        discipline="ELECTRICAL",
        threshold=0.80,
    )

    assert incident_id is None
    assert score == -1.0