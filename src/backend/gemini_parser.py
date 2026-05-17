"""
gemini_parser.py

Purpose:
Parse structured model output into backend fields needed by the MVP pipeline.

This utility is meant to be called after the queue/worker runs the model and
before the backend updates database-backed incident/report records.
"""
import json
import re

DISCIPLINES = [
    "FARE COLLECTION",
    "BUILDINGS",
    "COMMS",
    "ELEVATOR AND ESCALATOR",
    "GROUNDS",
    "MECHANICAL",
    "SYSTEM SERVICE",
    "STRUCTURES",
    "TRACK",
    "ELECTRICAL",
    "RSS",
    "UNCLASSIFIED",
]

PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

def _clean_value(value: str | None) -> str | None:
    """
    Remove extra whitespace and surrounding quotes from one parsed field.
    """
    if value is None:
        return None
    return value.strip().strip('"').strip("'")


def _extract_field(response_text: str, field_name: str) -> str | None:
    """
    Find one field in the raw model response.

    Example:
    issue_priority: LOW

    Returns only the value after the colon.
    """
    pattern = rf"^{field_name}\s*:\s*(.+)$"
    match = re.search(pattern, response_text, re.IGNORECASE | re.MULTILINE)

    if not match:
        return None

    return _clean_value(match.group(1))


def parse_classification(response_text: str) -> dict:
    """
    Parse raw JSON model text into structured backend fields.
    """
    # ======= CHANGED: Use native JSON parsing for Structured Outputs =======
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback for unexpected non-JSON output
        return {
            "issue_priority": None,
            "discipline": "UNCLASSIFIED",
            "vlm_summary": "Error: Invalid JSON output"
        }

    # Extract fields from the dictionary
    issue_priority = data.get("issue_priority")
    discipline = data.get("discipline")
    vlm_summary = data.get("vlm_summary")

    if issue_priority is not None:
        issue_priority = issue_priority.upper()

    if discipline is not None:
        discipline = discipline.upper()

    return {
        "issue_priority": issue_priority,
        "discipline": discipline,
        "vlm_summary": vlm_summary,
    }