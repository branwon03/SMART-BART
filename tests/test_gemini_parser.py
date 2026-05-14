import json
from src.backend.gemini_parser import parse_classification

def test_parse_classification_real_output():
    """
    Uses the JSON structured output format now required by the parser.
    """
    # Create a dictionary and convert to JSON string to mimic Gemini's output
    response_data = {
        "issue_priority": "LOW",
        "discipline": "GROUNDS",
        "vlm_summary": "Dense vegetation near a utility box with purple flowers."
    }
    response_text = json.dumps(response_data)

    parsed = parse_classification(response_text)

    assert parsed["issue_priority"] == "LOW"
    assert parsed["discipline"] == "GROUNDS"
    assert "utility box" in parsed["vlm_summary"]


def test_parse_classification_case_insensitivity():
    """
    Ensures the parser normalizes lowercase JSON values to UPPERCASE.
    """
    response_data = {
        "issue_priority": "medium",
        "discipline": "grounds",
        "vlm_summary": "Vegetation is overgrown near station grounds."
    }
    response_text = json.dumps(response_data)

    parsed = parse_classification(response_text)

    # The parser logic converts these to .upper()
    assert parsed["issue_priority"] == "MEDIUM"
    assert parsed["discipline"] == "GROUNDS"
    assert parsed["vlm_summary"] == "Vegetation is overgrown near station grounds."

def test_parse_classification_invalid_json_fallback():
    """
    Ensures that non-JSON text triggers the 'UNCLASSIFIED' fallback.
    """
    invalid_text = "This is not JSON code, it is just a plain sentence."
    
    parsed = parse_classification(invalid_text)
    
    assert parsed["discipline"] == "UNCLASSIFIED"
    assert "Error" in parsed["vlm_summary"]
    assert parsed["issue_priority"] is None