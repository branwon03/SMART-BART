"""
Tests for the /submissions endpoint contract (response shape, validation).
"""
from fastapi.testclient import TestClient

from src.backend.main import app
from tests.test_png_bytes import _make_png_bytes

client = TestClient(app)

EXPECTED_KEYS = {"incident_id", "submission_id", "description", "location_id", "timestamp"}


def test_submit_with_image():
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
    assert body["incident_id"]
    assert body["submission_id"]


def test_submit_multiple_images():
    png = _make_png_bytes()
    resp = client.post(
        "/api/submissions",
        files=[
            ("media", ("a.png", png, "image/png")),
            ("media", ("b.jpg", png, "image/jpeg")),
        ],
    )
    assert resp.status_code == 200
    assert set(resp.json().keys()) == EXPECTED_KEYS
    assert resp.json()["incident_id"]
    assert resp.json()["submission_id"]


def test_submit_description_only():
    resp = client.post(
        "/api/submissions",
        data={"description": "Spill on station floor"},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert set(body.keys()) == EXPECTED_KEYS
    assert body["description"] == "Spill on station floor"
    assert body["submission_id"]


def test_submit_unsupported_file_type():
    resp = client.post(
        "/api/submissions",
        files=[("media", ("video.mp4", b"\x00\x00", "video/mp4"))],
    )
    assert resp.status_code == 422

    body = resp.json()
    assert "Unsupported file type" in body["detail"]
    assert "mp4" in body["detail"]
