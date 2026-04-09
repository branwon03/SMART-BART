from math import sqrt
from sqlalchemy.orm import Session
from src.backend.database import PhotoReport

# Minimum cosine similarity required to attach a new report to an existing incident instead of creating new one
# to an existing incident instead of leaving it separate.
# Higher threshold = stricter grouping, fewer accidental merges.
GROUPING_THRESHOLD = 0.95

def cosine_similarity(vec_a, vec_b) -> float:
    """
    Compute cosine similarity b/t two embedding vectors.
    Return a value from -1.0 - 1.0:
    - closer to 1.0 -> very similar
    - closer to 0.0 -> not similar
    - -1.0 is used as our fallback (error) value when 
      similarity can't be computed.

    """

    # If either embedding is missing, can't compare them
    if vec_a is None or vec_b is None:
        return -1.0

    # Embeddings must have same dimension to compare
    if len(vec_a) != len(vec_b):
        return -1.0

    # Convert values to floats in case they come back in a type not directly safe for math operations
    a = [float(x) for x in vec_a]
    b = [float(x) for x in vec_b]

    # Math: Cosine similarity = dot(a,b) / (||a||*||b||)
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))

    # Avoid division by zero if either vector has no magnitude
    if norm_a == 0 or norm_b == 0:
        return -1.0
    return dot / (norm_a * norm_b)

def find_matching_incident(
    db: Session,
    new_embedding,
    discipline: str,
    user_context: str | None = None,
    threshold: float = GROUPING_THRESHOLD,
):
    """
    Try to group a newly processed photo into an existing incident.

    Current MVP grouping strategy:
    1. Only compare against completed photo reports
    2. Only compare within the same predicted discipline bucket
    3. Choose the candidate with the highest cosine similarity
    4. Reuse that incident only if similarity passes the threshold

    Why discipline filtering helps:
    - prevents unrelated categories from competing directly
    - reduces false matches across very different issue types

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

    # Compare only against photo reports that:
    # - already finished processing
    # - already have embeddings
    # - belong to the same predicted discipline
    candidates = (
        db.query(PhotoReport)
        .filter(PhotoReport.photo_report_discipline == discipline)
        .filter(PhotoReport.embedding.isnot(None))
        .filter(PhotoReport.photo_report_status == "Completed")
        .all()
    )

    best_incident_id = None
    best_score = -1.0

    # Find the strongest similarity match among all valid candidates
    for candidate in candidates:
        score = cosine_similarity(new_embedding, candidate.embedding)

        if score > best_score:
            best_score = score
            best_incident_id = candidate.incident_id

    # Only group when similarity is strong enough
    if best_score >= threshold:
        return best_incident_id, best_score

    # Otherwise keep the photo in its current incident
    return None, best_score