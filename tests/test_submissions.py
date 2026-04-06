"""
Tests for the /submissions endpoint contract (response shape, validation).
"""
from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

EXPECTED_KEYS = {"incident_id", "submission_id", "description", "timestamp"}


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


def test_submit_with_image():
    png = _make_png_bytes()
    resp = client.post(
        "/submissions",
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
        "/submissions",
        files=[
            ("media", ("a.png", png, "image/png")),
            ("media", ("b.jpg", png, "image/jpeg")),
        ],
    )
    assert resp.status_code == 200

    body = resp.json()
    assert set(body.keys()) == EXPECTED_KEYS
    assert body["incident_id"]
    assert body["submission_id"]


def test_submit_description_only():
    resp = client.post(
        "/submissions",
        data={"description": "Spill on station floor"},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert set(body.keys()) == EXPECTED_KEYS
    assert body["description"] == "Spill on station floor"
    assert body["incident_id"]


def test_submit_unsupported_file_type():
    resp = client.post(
        "/submissions",
        files=[("media", ("video.mp4", b"\x00\x00", "video/mp4"))],
    )
    assert resp.status_code == 422

    body = resp.json()
    assert "Unsupported file type" in body["detail"]
    assert "mp4" in body["detail"]
