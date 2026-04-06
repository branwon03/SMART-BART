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


def test_build_query_with_description_appends_user_context():
    query = build_query("Escalator is making a loud grinding noise")

    assert "User Context:" in query
    assert "Escalator is making a loud grinding noise" in query
    assert "You are a BART maintenance issue classifier." in query
