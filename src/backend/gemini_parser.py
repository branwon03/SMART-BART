"""
gemini_parser.py

Purpose:
Parse structured model output into backend fields needed by the MVP pipeline.

This utility is meant to be called after the queue/worker runs the model and
before the backend updates database-backed incident/report records.
"""

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
    Parse raw model text into structured backend fields.

    Expected output fields:
    - issue_priority
    - discipline
    - vlm_summary
    """
    issue_priority = _extract_field(response_text, "issue_priority")
    discipline = _extract_field(response_text, "discipline")
    vlm_summary = _extract_field(response_text, "vlm_summary")

    if issue_priority is not None:
        issue_priority = issue_priority.upper()

    if discipline is not None:
        discipline = discipline.upper()

    return {
        "issue_priority": issue_priority,
        "discipline": discipline,
        "vlm_summary": vlm_summary,
    }