from math import sqrt
from sqlalchemy.orm import Session
from src.backend.database import PhotoReport, _USE_SQLITE

# Minimum cosine similarity required to attach a new report to an existing incident
# instead of leaving it separate.
# Higher threshold = stricter grouping, fewer accidental merges.
GROUPING_THRESHOLD = 0.94


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


def _get_best_match_postgres(db: Session, new_embedding, discipline: str):
    """
    Postgres/pgvector path: ask the database for the nearest candidate
    by cosine distance.

    Returns:
    - (incident_id, cosine_distance) for the best candidate
    - None if no candidates exist
    """
    distance_expr = PhotoReport.embedding.cosine_distance(new_embedding).label("distance")

    return (
        db.query(PhotoReport.incident_id, distance_expr)
        .filter(PhotoReport.photo_report_discipline == discipline)
        .filter(PhotoReport.embedding.isnot(None))
        .filter(PhotoReport.photo_report_status == "Completed")
        .order_by(distance_expr.asc())
        .first()
    )


def _get_best_match_sqlite(db: Session, new_embedding, discipline: str):
    """
    SQLite/test path: compute the best similarity in Python because the embedding
    column is JSON in SQLite and does not support pgvector operators.

    Returns:
    - (incident_id, cosine_similarity) for the best candidate
    - None if no candidates exist
    """
    candidates = (
        db.query(PhotoReport)
        .filter(PhotoReport.photo_report_discipline == discipline)
        .filter(PhotoReport.embedding.isnot(None))
        .filter(PhotoReport.photo_report_status == "Completed")
        .all()
    )

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
    threshold: float = GROUPING_THRESHOLD,
):
    """
    Try to group a newly processed photo into an existing incident.

    Grouping strategy:
    1. Only compare within the same predicted discipline bucket
    2. Only compare against reports that have already been fully processed and have embeddings
    3. In Postgres, use pgvector cosine distance to find the nearest candidate
    4. In SQLite tests, use a Python fallback because embeddings are stored as JSON
    5. Reuse that incident only if similarity passes the threshold

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

    # SQLite/test path: compute similarity in Python because SQLite stores embeddings as JSON
    if _USE_SQLITE:
        best_match = _get_best_match_sqlite(db, new_embedding, discipline)

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
    best_match = _get_best_match_postgres(db, new_embedding, discipline)

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