"""
This module implements the core grouping logic to determine whether a newly processed 
photo report should be attached to an existing incident or should start a new incident.
"""

from datetime import timedelta
from math import sqrt
from sqlalchemy.orm import Session
from src.backend.database import Incident, PhotoReport, _USE_SQLITE

# Minimum cosine similarity required to attach a new report to an existing incident
# instead of leaving it separate.
# Higher threshold = stricter grouping, fewer accidental merges.
GROUPING_THRESHOLD = 0.94

# Only compare against recent reports from the same location.
# This helps reduce accidental matches to old historical incidents.
GROUPING_TIME_WINDOW_HOURS = 48

# Only group into incidents that are still active.
# This prevents a new report from being attached to an old closed/completed incident.
ACTIVE_INCIDENT_STATUSES = ("New", "In-Progress")


def _cosine_similarity_fallback(vec_a, vec_b) -> float:
    """
    SQLite/test fallback only.

    In production Postgres, we use pgvector cosine distance directly in the DB.
    In SQLite tests, embeddings are stored as JSON, so we need a lightweight
    Python fallback to preserve testability.

    Return a value from -1.0 to 1.0:
    - closer to 1.0 -> very similar
    - closer to 0.0 -> not similar
    - -1.0 is used as our fallback/error value when similarity can't be computed
    """

    # If either embedding is missing, we cannot compare them
    if vec_a is None or vec_b is None:
        return -1.0

    # Embeddings must have the same dimension to compare
    if len(vec_a) != len(vec_b):
        return -1.0

    # Convert values to floats in case they come back in a type that's not directly safe for math operations
    a = [float(x) for x in vec_a]
    b = [float(x) for x in vec_b]

    # Math: cosine similarity = dot(a, b) / (||a|| * ||b||)
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))

    # Avoid division by zero if either vector has no magnitude
    if norm_a == 0 or norm_b == 0:
        return -1.0

    return dot / (norm_a * norm_b)


def _get_best_match_postgres(
    db: Session,
    new_embedding,
    discipline: str,
    location_id: str | None,
    submitted_at,
    time_window_hours: int,
    exclude_evidence_id: str | None = None,
):
    """
    Postgres/pgvector path: ask the database for the nearest candidate
    by cosine distance.

    Candidate filtering now includes:
    - same predicted discipline
    - same recent time window
    - only photo reports that have completed processing
    - only parent incidents that are still active
    - same location IF a location is available
    - exclude the current photo so it cannot match itself

    Returns:
    - (incident_id, cosine_distance) for the best candidate
    - None if no candidates exist
    """

    # Compute the beginning of the allowed historical comparison window
    window_start = submitted_at - timedelta(hours=time_window_hours)

    # pgvector cosine distance expression
    # Smaller distance = closer match
    distance_expr = PhotoReport.embedding.cosine_distance(new_embedding).label("distance")

    query = (
        db.query(PhotoReport.incident_id, distance_expr)
        .join(Incident, PhotoReport.incident_id == Incident.incident_id)
        .filter(PhotoReport.photo_report_discipline == discipline)
        .filter(PhotoReport.embedding.isnot(None))
        .filter(PhotoReport.photo_report_status == "Completed")
        .filter(PhotoReport.submitted_at.isnot(None))
        .filter(PhotoReport.submitted_at >= window_start)
        .filter(PhotoReport.submitted_at <= submitted_at)
        .filter(Incident.status.in_(ACTIVE_INCIDENT_STATUSES))
    )

    # If location metadata is available, use it as an additional narrowing filter.
    # If location is missing, still allow grouping fallback using discipline + time + active incidents.
    if location_id:
        query = query.filter(PhotoReport.photo_location_id == location_id)

    # Exclude the current photo report so it cannot be returned as its own nearest neighbor.
    if exclude_evidence_id:
        query = query.filter(PhotoReport.evidence_id != exclude_evidence_id)

    return query.order_by(distance_expr.asc()).first()


def _get_best_match_sqlite(
    db: Session,
    new_embedding,
    discipline: str,
    location_id: str | None,
    submitted_at,
    time_window_hours: int,
    exclude_evidence_id: str | None = None,
):
    """
    SQLite/test path: compute the best similarity in Python because the embedding
    column is JSON in SQLite and does not support pgvector operators.

    Even though similarity is computed in Python here, we still apply the same
    candidate narrowing rules as production:
    - same discipline
    - same recent time window
    - completed photo reports only
    - active parent incidents only
    - same location IF a location is available
    - exclude the current photo so it cannot match itself

    Returns:
    - (incident_id, cosine_similarity) for the best candidate
    - None if no candidates exist
    """

    # Compute the beginning of the allowed historical comparison window
    window_start = submitted_at - timedelta(hours=time_window_hours)

    query = (
        db.query(PhotoReport)
        .join(Incident, PhotoReport.incident_id == Incident.incident_id)
        .filter(PhotoReport.photo_report_discipline == discipline)
        .filter(PhotoReport.embedding.isnot(None))
        .filter(PhotoReport.photo_report_status == "Completed")
        .filter(PhotoReport.submitted_at.isnot(None))
        .filter(PhotoReport.submitted_at >= window_start)
        .filter(PhotoReport.submitted_at <= submitted_at)
        .filter(Incident.status.in_(ACTIVE_INCIDENT_STATUSES))
    )

    # If location metadata is available, use it as an additional narrowing filter.
    # If location is missing, still allow grouping fallback using discipline + time + active incidents.
    if location_id:
        query = query.filter(PhotoReport.photo_location_id == location_id)

    # Exclude the current photo report so it cannot be returned as its own best match.
    if exclude_evidence_id:
        query = query.filter(PhotoReport.evidence_id != exclude_evidence_id)

    candidates = query.all()

    best_incident_id = None
    best_score = -1.0

    # Compare the new embedding against each stored embedding
    for candidate in candidates:
        score = _cosine_similarity_fallback(new_embedding, candidate.embedding)

        if score > best_score:
            best_score = score
            best_incident_id = candidate.incident_id

    if best_incident_id is None:
        return None

    return best_incident_id, best_score


def find_matching_incident(
    db: Session,
    new_embedding,
    discipline: str,
    user_context: str | None = None,    # user_context is kept in the signature for future grouping filters
                                        # such as text/location/time-aware matching refinements
    location_id: str | None = None,
    submitted_at=None,
    threshold: float = GROUPING_THRESHOLD,
    time_window_hours: int = GROUPING_TIME_WINDOW_HOURS,
    exclude_evidence_id: str | None = None,
):
    """
    Try to group a newly processed photo into an existing incident.

    Grouping strategy:
    1. Only compare within the same predicted discipline bucket
    2. Only compare within the recent time window
    3. Only compare against parent incidents that are still active
    4. Only compare against reports that have already been fully processed and have embeddings
    5. If location metadata is available, use it to narrow candidates further
    6. Exclude the current photo so it cannot self-match
    7. In Postgres, use pgvector cosine distance to find the nearest candidate
    8. In SQLite tests, use a Python fallback because embeddings are stored as JSON
    9. Reuse that incident only if similarity passes the threshold

    Robust fallback behavior:
    - if location exists -> grouping becomes more context-aware by requiring same location
    - if location is missing -> grouping can still proceed using discipline + time + active incidents

    Returns:
    - (incident_id, score) if a strong match is found
    - (None, score) if candidates were checked but none passed threshold
    - (None, None) if grouping could not be attempted
    """

    # If we have no embedding, we cannot do similarity-based grouping
    if new_embedding is None:
        return None, None

    # Skip grouping when classification is missing or too weak
    if not discipline or discipline in {"UNKNOWN", "UNCLASSIFIED"}:
        return None, None

    # Location is preferred but not required.
    # If available, it narrows grouping candidates further.
    # If missing, grouping can still fall back to discipline + time + active incidents.

    # We still require a submission timestamp so we can restrict comparisons to a recent window
    if submitted_at is None:
        return None, None

    # SQLite/test path: compute similarity in Python because SQLite stores embeddings as JSON
    if _USE_SQLITE:
        best_match = _get_best_match_sqlite(
            db,
            new_embedding,
            discipline,
            location_id,
            submitted_at,
            time_window_hours,
            exclude_evidence_id,
        )

        # If no candidates exist at all, create a new incident
        if best_match is None:
            return None, -1.0

        best_incident_id, best_score = best_match

        # Only reuse the incident if it passes the similarity threshold
        if best_score >= threshold:
            return best_incident_id, best_score

        # Otherwise, keep it separate but return the score for debugging/monitoring
        return None, best_score

    # Postgres path: let the database find the nearest candidate by cosine distance
    best_match = _get_best_match_postgres(
        db,
        new_embedding,
        discipline,
        location_id,
        submitted_at,
        time_window_hours,
        exclude_evidence_id,
    )

    # If no candidates exist at all, return "no match"
    if best_match is None:
        return None, -1.0

    # Convert cosine distance to cosine similarity for threshold comparison
    best_incident_id, best_distance = best_match

    # pgvector cosine distance = 1 - cosine similarity
    best_score = 1.0 - float(best_distance)

    # Only reuse the incident if it passes the similarity threshold
    if best_score >= threshold:
        return best_incident_id, best_score

    # If it does not pass the threshold, keep it separate but return the score
    return None, best_score