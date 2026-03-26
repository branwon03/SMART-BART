from src.backend.gemini_parser import parse_classification


def test_parse_classification_real_output():
    """
    Uses the real structured output format validated during MVP testing.
    """
    response_text = """issue_priority: LOW
discipline: GROUNDS
vlm_summary: Dense vegetation with small purple flowers and dry leaves is overgrown on the ground, partially obscuring a utility box."""

    parsed = parse_classification(response_text)

    assert parsed["issue_priority"] == "LOW"
    assert parsed["discipline"] == "GROUNDS"
    assert "utility box" in parsed["vlm_summary"]


def test_parse_classification_with_quotes():
    """
    Makes sure the parser still works if the model returns quoted values.
    """
    response_text = """issue_priority: "medium"
discipline: "grounds"
vlm_summary: "Vegetation is overgrown near station grounds." """

    parsed = parse_classification(response_text)

    assert parsed["issue_priority"] == "MEDIUM"
    assert parsed["discipline"] == "GROUNDS"
    assert parsed["vlm_summary"] == "Vegetation is overgrown near station grounds."