from src.backend.inference import build_query


def test_build_query_without_description_uses_new_maintenance_prompt():
    query = build_query()

    assert "You are a BART maintenance issue classifier." in query
    assert "Brief Summary, a Discipline, and a Priority Level" in query
    assert "LOW" in query
    assert "STANDARD" in query
    assert "HIGH" in query
    assert "CRITICAL" in query
    assert "- UNCLASSIFIED:" in query


def test_build_query_with_description_marks_user_text_as_primary_evidence():
    query = build_query("Escalator is making a loud grinding noise")

    assert "User Description" in query
    assert "primary evidence" in query
    assert "secondary context" not in query
    assert "Escalator is making a loud grinding noise" in query
