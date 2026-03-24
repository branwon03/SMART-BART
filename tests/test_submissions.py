"""
Tests for the /submissions endpoint contract (response shape, validation).
"""
from datetime import datetime
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

MOCK_RESULT = {
    "discipline": "ELECTRICAL",
    "description": "Exposed wiring near platform edge",
    "num_images": 1,
    "timestamp": datetime.utcnow().isoformat(),
    "submission_id": "00000000000000000000000000000000",
}

EXPECTED_KEYS = {"incident_id", "submission_id", "discipline", "description", "num_images", "timestamp"}


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


@patch("src.backend.main.chat_with_media", return_value=MOCK_RESULT)
def test_submit_with_image(mock_chat):
    png = _make_png_bytes()

    def _side_effect(*args, **kwargs):
        return {**MOCK_RESULT, "submission_id": kwargs.get("submission_id")}

    mock_chat.side_effect = _side_effect
    resp = client.post(
        "/submissions",
        files=[("media", ("test.png", png, "image/png"))],
        data={"description": "Exposed wiring near platform edge"},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert set(body.keys()) == EXPECTED_KEYS
    assert body["discipline"] in [
        "FARE COLLECTION", "BUILDINGS", "COMMS", "ELEVATOR AND ESCALATOR",
        "GROUNDS", "MECHANICAL", "SYSTEM SERVICE", "STRUCTURES",
        "TRACK", "ELECTRICAL", "RSS",
    ]
    assert body["description"] == "Exposed wiring near platform edge"
    assert body["num_images"] == 1
    assert body["timestamp"]

    mock_chat.assert_called_once()

    submission_id = mock_chat.call_args.kwargs["submission_id"]
    uuid.UUID(submission_id)
    assert body["submission_id"] == submission_id


@patch("src.backend.main.chat_with_media")
def test_submit_multiple_images(mock_chat):
    mock_chat.side_effect = lambda *a, **kw: {
        "discipline": "BUILDINGS",
        "description": None,
        "num_images": 2,
        "timestamp": datetime.utcnow().isoformat(),
        "submission_id": kw.get("submission_id"),
    }
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
    assert body["num_images"] == 2
    assert body["discipline"] == "BUILDINGS"

    mock_chat.assert_called_once()


@patch("src.backend.main.chat_with_media")
def test_submit_description_only(mock_chat):
    mock_chat.side_effect = lambda *a, **kw: {
        "discipline": "SYSTEM SERVICE",
        "description": "Spill on station floor",
        "num_images": 0,
        "timestamp": datetime.utcnow().isoformat(),
        "submission_id": kw.get("submission_id"),
    }
    resp = client.post(
        "/submissions",
        data={"description": "Spill on station floor"},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert set(body.keys()) == EXPECTED_KEYS
    assert body["discipline"] == "SYSTEM SERVICE"
    assert body["description"] == "Spill on station floor"
    assert body["num_images"] == 0

    mock_chat.assert_called_once()


def test_submit_unsupported_file_type():
    resp = client.post(
        "/submissions",
        files=[("media", ("video.mp4", b"\x00\x00", "video/mp4"))],
    )
    assert resp.status_code == 422

    body = resp.json()
    assert "Unsupported file type" in body["detail"]
    assert "mp4" in body["detail"]


@patch("src.backend.main.chat_with_media", return_value=None)
def test_submit_api_failure_returns_502(mock_chat):
    png = _make_png_bytes()
    resp = client.post(
        "/submissions",
        files=[("media", ("test.png", png, "image/png"))],
    )
    assert resp.status_code == 502
    assert "Inference API unavailable" in resp.json()["detail"]
