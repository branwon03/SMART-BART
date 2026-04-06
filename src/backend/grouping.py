from math import sqrt
from sqlalchemy.orm import Session
from src.backend.database import Incident, PhotoReport

# Minimum cosine similarity required to attach a new report to an existing incident instead of creating new one
GROUPING_THRESHOLD = 0.60   # Can tune later

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
    Try to find an existing incident that this new report should be grouped into.
    MVP Grouping Rule:
    1. Only compare against reports from same discipline
    2. Only compare against rows that already have embeddings
    3. Choose highest similarity score
    4. Reuse that incident_id only if score passes threshold

    Returns:
    - (incident_id, score) if we found a strong enough match
    - (None, score) if we compared candidates but none passed threshold
    - (None, None) if grouping could not even be attempted
    """
    if new_embedding is None:
        return None, None
    
    # Skip grouping for missing/weak classifications
    # We only want to compare inside a real discipline bucket
    if not discipline or discipline in {"UNKNOWN", "UNCLASSIFIED"}:
        return None, None

    # Pull all previously saved photo reports that belong to incidents of same discipline + already have embedding stored
    candidates_query = (
        db.query(PhotoReport, Incident)
        .join(Incident, Incident.incident_id == PhotoReport.incident_id)
        .filter(Incident.discipline == discipline)
        .filter(PhotoReport.embedding.isnot(None))
    )

    #if user_context:
        #candidates_query = candidates_query.filter(PhotoReport.user_context == user_context)

    candidates = candidates_query.all()

    # Track strongest match we see
    best_incident_id = None
    best_score = -1.0

    # Compare the new embedding against each stored embedding
    for photo_report, incident in candidates:
        score = cosine_similarity(new_embedding, photo_report.embedding)
        if score > best_score:
            best_score = score
            best_incident_id = incident.incident_id

    # If best similarity passes threshold, group into that incident
    if best_score >= threshold:
        return best_incident_id, best_score
    # Else, signal that no existing incident was a strong enough match
    return None, best_score