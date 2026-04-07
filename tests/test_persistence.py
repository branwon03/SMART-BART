"""
Tests for the submission → DB persistence pipeline.
"""
from fastapi.testclient import TestClient

from src.backend.main import app

client = TestClient(app)


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


# ── submission persists Incident + PhotoReport ────────────────────────────────


def test_submission_persists_and_returns_incident_id():
    resp = client.post(
        "/api/submissions",
        files=[("media", ("test.png", _make_png_bytes(), "image/png"))],
        data={"description": "Exposed wiring near platform edge"},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert set(body.keys()) == {"incident_id", "description", "timestamp"}
    assert body["description"] == "Exposed wiring near platform edge"

    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc["incident_id"] == body["incident_id"]
    assert inc["discipline"] is None
    assert inc["status"] == "New"
    assert inc["vlm_summary"] == "Exposed wiring near platform edge"

    reports = client.get(f"/api/photo-reports/{body['incident_id']}").json()
    assert len(reports) == 1
    rpt = reports[0]
    assert set(rpt.keys()) == {
        "evidence_id",
        "incident_id",
        "image_url",
        "submitted_at",
        "user_context",
        "found_priority",
    }
    assert rpt["incident_id"] == body["incident_id"]
    assert rpt["user_context"] == "Exposed wiring near platform edge"


# ── GET /api/incidents accumulates multiple submissions ─────────────────────────


def test_incidents_accumulate():
    png = _make_png_bytes()

    r1 = client.post(
        "/api/submissions",
        files=[("media", ("a.png", png, "image/png"))],
        data={"description": "Broken escalator"},
    )
    r2 = client.post(
        "/api/submissions",
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


# ── photo reports are scoped to their incident ──────────────────────────────────


def test_photo_reports_scoped_to_incident():
    png = _make_png_bytes()

    r1 = client.post(
        "/api/submissions",
        files=[("media", ("a.png", png, "image/png"))],
        data={"description": "Issue A"},
    )
    r2 = client.post(
        "/api/submissions",
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

    assert client.get("/api/photo-reports/does-not-exist").json() == []


# ── new incidents have null discipline until processed ────────────────────────


def test_new_incident_has_null_discipline():
    client.post(
        "/api/submissions",
        files=[("media", ("a.png", _make_png_bytes(), "image/png"))],
        data={"description": "Cracked wall"},
    )

    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    assert incidents[0]["discipline"] is None


# ── GET /api/images returns 404 for unknown evidence_id ────────────────────────


def test_get_image_unknown_returns_404():
    resp = client.get("/api/images/does-not-exist")
    assert resp.status_code == 404


# ── submission with image persists image_url and serves file ───────────────────


def test_submission_persists_image_and_serves_it():
    png = _make_png_bytes()

    resp = client.post(
        "/api/submissions",
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


# ── text-only submission creates incident but no photo reports ────────────────


def test_text_only_submission_has_no_photo_reports():
    resp = client.post(
        "/api/submissions",
        data={"description": "Spill on floor"},
    )
    assert resp.status_code == 200

    reports = client.get(f"/api/photo-reports/{resp.json()['incident_id']}").json()
    assert reports == []


# ── text-only submission persists incident with description ───────────────────


def test_text_only_submission_persists_incident():
    resp = client.post(
        "/api/submissions",
        data={"description": "Spill on station floor"},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["description"] == "Spill on station floor"

    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    assert incidents[0]["vlm_summary"] == "Spill on station floor"
    assert incidents[0]["discipline"] is None
