"""
Tests for the /api/submissions endpoint (the proxied path the frontend uses).
"""
from fastapi.testclient import TestClient

from src.backend.main import app
from tests.test_png_bytes import _make_png_bytes

client = TestClient(app)

EXPECTED_KEYS = {"incident_id", "submission_id", "description", "timestamp"}


def test_api_submissions_with_image():
    """POST /api/submissions with an image returns the correct response shape."""
    png = _make_png_bytes()
    resp = client.post(
        "/api/submissions",
        files=[("media", ("test.png", png, "image/png"))],
        data={"description": "Exposed wiring near platform edge"},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert set(body.keys()) == EXPECTED_KEYS
    assert body["description"] == "Exposed wiring near platform edge"
    assert body["timestamp"]


def test_api_submissions_persists_incident_as_new():
    """Submission creates an incident with status 'New' and null discipline."""
    png = _make_png_bytes()
    resp = client.post(
        "/api/submissions",
        files=[("media", ("test.png", png, "image/png"))],
        data={"description": "Broken escalator handrail"},
    )
    assert resp.status_code == 200
    incident_id = resp.json()["incident_id"]

    incidents = client.get("/api/incidents").json()
    match = [i for i in incidents if i["incident_id"] == incident_id]
    assert len(match) == 1
    assert match[0]["status"] == "New"
    assert match[0]["discipline"] is None


def test_api_submissions_description_only():
    """POST /api/submissions with only a description (no media) succeeds."""
    resp = client.post(
        "/api/submissions",
        data={"description": "Spill on station floor"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == EXPECTED_KEYS
    assert body["description"] == "Spill on station floor"


def test_api_submissions_rejects_unsupported_file_type():
    """POST /api/submissions with an unsupported file type returns 422."""
    resp = client.post(
        "/api/submissions",
        files=[("media", ("video.mp4", b"\x00\x00", "video/mp4"))],
    )
    assert resp.status_code == 422
    assert "Unsupported file type" in resp.json()["detail"]


def test_api_submissions_persists_reporter_fields():
    """Reporter name and contact are stored and returned on photo reports."""
    png = _make_png_bytes()
    resp = client.post(
        "/api/submissions",
        files=[("media", ("test.png", png, "image/png"))],
        data={
            "description": "Wet floor",
            "reporter_name": "Jamie Test",
            "reporter_contact": "555-0100",
        },
    )
    assert resp.status_code == 200
    incident_id = resp.json()["incident_id"]
    reports = client.get(f"/api/photo-reports/{incident_id}").json()
    assert len(reports) == 1
    assert reports[0]["reporter_name"] == "Jamie Test"
    assert reports[0]["reporter_contact"] == "555-0100"
