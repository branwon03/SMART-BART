"""
Tests for the submission → DB persistence pipeline.
"""
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.backend.main import app

client = TestClient(app)

MOCK_INFERENCE = {
    "submission_id": "will-be-overridden",
    "discipline": "ELECTRICAL",
    "description": "Exposed wiring near platform edge",
    "num_images": 1,
    "timestamp": datetime.utcnow().isoformat(),
}


def _make_png_bytes() -> bytes:
    import struct, zlib
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


# ── RED-GREEN #1: submission persists Incident + PhotoReport ──────────────────

@patch("src.backend.main.chat_with_media")
def test_submission_persists_and_returns_incident_id(mock_chat):
    def _side_effect(*args, **kwargs):
        return {**MOCK_INFERENCE, "submission_id": kwargs.get("submission_id")}

    mock_chat.side_effect = _side_effect

    resp = client.post(
        "/submissions",
        files=[("media", ("test.png", _make_png_bytes(), "image/png"))],
        data={"description": "Exposed wiring near platform edge"},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert "incident_id" in body
    assert "submission_id" in body
    assert body["discipline"] == "ELECTRICAL"
    assert body["description"] == "Exposed wiring near platform edge"
    assert body["num_images"] == 1

    # Verify DB persistence via the GET endpoints
    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc["incident_id"] == body["incident_id"]
    assert inc["discipline"] == "ELECTRICAL"
    assert inc["status"] == "Open"
    assert inc["vlm_summary"] == "Exposed wiring near platform edge"

    reports = client.get(f"/api/photo-reports/{body['incident_id']}").json()
    assert len(reports) == 1
    rpt = reports[0]
    assert rpt["submission_id"] == body["submission_id"]
    assert rpt["incident_id"] == body["incident_id"]
    assert rpt["user_context"] == "Exposed wiring near platform edge"


# ── RED-GREEN #2: GET /api/incidents accumulates multiple submissions ─────────

@patch("src.backend.main.chat_with_media")
def test_incidents_accumulate(mock_chat):
    mock_chat.side_effect = lambda *a, **kw: {
        **MOCK_INFERENCE,
        "submission_id": kw.get("submission_id"),
    }
    png = _make_png_bytes()

    # Two separate submissions
    r1 = client.post(
        "/submissions",
        files=[("media", ("a.png", png, "image/png"))],
        data={"description": "Broken escalator"},
    )
    r2 = client.post(
        "/submissions",
        files=[("media", ("b.png", png, "image/png"))],
        data={"description": "Graffiti on wall"},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200

    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 2
    ids = {i["incident_id"] for i in incidents}
    assert r1.json()["incident_id"] in ids
    assert r2.json()["incident_id"] in ids


# ── RED-GREEN #3: photo reports are scoped to their incident ──────────────────

@patch("src.backend.main.chat_with_media")
def test_photo_reports_scoped_to_incident(mock_chat):
    mock_chat.side_effect = lambda *a, **kw: {
        **MOCK_INFERENCE,
        "submission_id": kw.get("submission_id"),
    }
    png = _make_png_bytes()

    r1 = client.post(
        "/submissions",
        files=[("media", ("a.png", png, "image/png"))],
        data={"description": "Issue A"},
    )
    r2 = client.post(
        "/submissions",
        files=[("media", ("b.png", png, "image/png"))],
        data={"description": "Issue B"},
    )
    id1 = r1.json()["incident_id"]
    id2 = r2.json()["incident_id"]

    rpt1 = client.get(f"/api/photo-reports/{id1}").json()
    rpt2 = client.get(f"/api/photo-reports/{id2}").json()
    assert len(rpt1) == 1
    assert len(rpt2) == 1
    assert rpt1[0]["user_context"] == "Issue A"
    assert rpt2[0]["user_context"] == "Issue B"

    # Non-existent incident returns empty
    assert client.get("/api/photo-reports/does-not-exist").json() == []


# ── RED-GREEN #4: inference failure → 502, no DB rows ────────────────────────

@patch("src.backend.main.chat_with_media", return_value=None)
def test_inference_failure_returns_502_no_persistence(mock_chat):
    png = _make_png_bytes()
    resp = client.post(
        "/submissions",
        files=[("media", ("test.png", png, "image/png"))],
        data={"description": "Something broken"},
    )
    assert resp.status_code == 502
    assert "Inference API unavailable" in resp.json()["detail"]

    # Nothing persisted
    assert client.get("/api/incidents").json() == []


# ── RED-GREEN #5: discipline values are uppercase (frontend dashboard depends on this) ─

UPPERCASE_DISCIPLINES = {
    "FARE COLLECTION", "BUILDINGS", "COMMS", "ELEVATOR AND ESCALATOR",
    "GROUNDS", "MECHANICAL", "SYSTEM SERVICE", "STRUCTURES",
    "TRACK", "ELECTRICAL", "RSS",
}


@patch("src.backend.main.chat_with_media")
def test_incidents_discipline_is_uppercase(mock_chat):
    """GET /api/incidents must return discipline in uppercase so the dashboard can filter."""
    mock_chat.side_effect = lambda *a, **kw: {
        **MOCK_INFERENCE,
        "submission_id": kw.get("submission_id"),
        "discipline": "BUILDINGS",
    }
    client.post(
        "/submissions",
        files=[("media", ("a.png", _make_png_bytes(), "image/png"))],
        data={"description": "Cracked wall"},
    )

    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    assert incidents[0]["discipline"] in UPPERCASE_DISCIPLINES
    assert incidents[0]["discipline"] == "BUILDINGS"


# ── RED-GREEN #6: GET /api/images returns 404 for unknown evidence_id ────────

def test_get_image_unknown_returns_404():
    resp = client.get("/api/images/does-not-exist")
    assert resp.status_code == 404


# ── RED-GREEN #7: submission with image persists image_url and serves file ────

@patch("src.backend.main.chat_with_media")
def test_submission_persists_image_and_serves_it(mock_chat):
    mock_chat.side_effect = lambda *a, **kw: {
        **MOCK_INFERENCE,
        "submission_id": kw.get("submission_id"),
    }
    png = _make_png_bytes()

    resp = client.post(
        "/submissions",
        files=[("media", ("test.png", png, "image/png"))],
        data={"description": "Broken light fixture"},
    )
    assert resp.status_code == 200
    body = resp.json()

    reports = client.get(f"/api/photo-reports/{body['incident_id']}").json()
    assert len(reports) == 1
    rpt = reports[0]

    assert rpt["image_url"] is not None
    assert rpt["image_url"].startswith("/api/images/")

    img_resp = client.get(rpt["image_url"])
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"] in ("image/png", "image/jpeg", "image/webp")
    assert len(img_resp.content) > 0


# ── RED-GREEN #8: text-only submission still has null image_url ───────────────

@patch("src.backend.main.chat_with_media")
def test_text_only_submission_has_null_image_url(mock_chat):
    mock_chat.side_effect = lambda *a, **kw: {
        "submission_id": kw.get("submission_id"),
        "discipline": "SYSTEM SERVICE",
        "description": "Spill on floor",
        "num_images": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }
    resp = client.post(
        "/submissions",
        data={"description": "Spill on floor"},
    )
    assert resp.status_code == 200

    reports = client.get(f"/api/photo-reports/{resp.json()['incident_id']}").json()
    assert len(reports) == 1
    assert reports[0]["image_url"] is None


# ── RED-GREEN #9: text-only submission (no images) persists ───────────────────

@patch("src.backend.main.chat_with_media")
def test_text_only_submission_persists(mock_chat):
    mock_chat.side_effect = lambda *a, **kw: {
        "submission_id": kw.get("submission_id"),
        "discipline": "SYSTEM SERVICE",
        "description": "Spill on station floor",
        "num_images": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }

    resp = client.post(
        "/submissions",
        data={"description": "Spill on station floor"},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["discipline"] == "SYSTEM SERVICE"
    assert body["num_images"] == 0

    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    assert incidents[0]["discipline"] == "SYSTEM SERVICE"
    assert incidents[0]["vlm_summary"] == "Spill on station floor"
