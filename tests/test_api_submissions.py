"""
Tests for the /api/submissions endpoint (the proxied path the frontend uses).
"""
from fastapi.testclient import TestClient

from src.backend.main import app

client = TestClient(app)

EXPECTED_KEYS = {"incident_id", "submission_id""description", "timestamp"}


def _make_png_bytes() -> bytes:
    import struct
    import zlib
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = b"IHDR" + ihdr_data
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + ihdr + struct.pack(">I", zlib.crc32(ihdr) & 0xFFFFFFFF)
    raw = zlib.compress(b"\x00\x00\x00\x00")
    idat = b"IDAT" + raw
    idat_chunk = struct.pack(">I", len(raw)) + idat + struct.pack(">I", zlib.crc32(idat) & 0xFFFFFFFF)
    iend = b"IEND"
    iend_chunk = struct.pack(">I", 0) + iend + struct.pack(">I", zlib.crc32(iend) & 0xFFFFFFFF)
    return sig + ihdr_chunk + idat_chunk + iend_chunk


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
