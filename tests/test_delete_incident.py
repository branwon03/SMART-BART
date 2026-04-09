"""Tests for DELETE /api/incidents/{incident_id}."""
import struct
import zlib

from fastapi.testclient import TestClient

from src.backend.main import app

client = TestClient(app)


def _make_tiny_png() -> bytes:
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


def _create_incident(description: str = "Test issue") -> str:
    """Create an incident via the submissions endpoint and return its ID."""
    resp = client.post("/api/submissions", data={"description": description})
    assert resp.status_code == 200
    return resp.json()["incident_id"]


def test_delete_existing_incident_returns_success():
    incident_id = _create_incident()

    resp = client.delete(f"/api/incidents/{incident_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted_incident_id"] == incident_id


def test_delete_nonexistent_incident_returns_404():
    resp = client.delete("/api/incidents/does-not-exist")

    assert resp.status_code == 404


def test_deleted_incident_no_longer_listed():
    incident_id = _create_incident("Leak near track")

    client.delete(f"/api/incidents/{incident_id}")

    incidents = client.get("/api/incidents").json()
    assert all(i["incident_id"] != incident_id for i in incidents)


def test_delete_removes_associated_photo_reports():
    png = _make_tiny_png()
    resp = client.post(
        "/api/submissions",
        files=[("media", ("img.png", png, "image/png"))],
        data={"description": "Crack in platform"},
    )
    incident_id = resp.json()["incident_id"]

    reports_before = client.get(f"/api/photo-reports/{incident_id}").json()
    assert len(reports_before) > 0

    client.delete(f"/api/incidents/{incident_id}")

    reports_after = client.get(f"/api/photo-reports/{incident_id}").json()
    assert len(reports_after) == 0
