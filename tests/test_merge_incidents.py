"""Tests for POST /api/incidents/{target_incident_id}/merge-photos."""
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


def _create_incident_with_images(description: str, num_images: int = 1) -> str:
    png = _make_tiny_png()
    files = [
        ("media", (f"img{n}.png", png, "image/png"))
        for n in range(num_images)
    ]
    resp = client.post("/api/submissions", files=files, data={"description": description})
    assert resp.status_code == 200
    return resp.json()["incident_id"]


def _set_target_discipline(db_session, incident_id: str, discipline: str) -> None:
    from src.backend.database import Incident

    row = db_session.query(Incident).filter(Incident.incident_id == incident_id).first()
    assert row is not None
    row.discipline = discipline
    db_session.commit()


def _set_photo_discipline(db_session, evidence_id: str, discipline: str) -> None:
    from src.backend.database import PhotoReport

    row = db_session.query(PhotoReport).filter(PhotoReport.evidence_id == evidence_id).first()
    assert row is not None
    row.photo_report_discipline = discipline
    db_session.commit()


def test_merge_photos_moves_rows_and_counts():
    target_id = _create_incident_with_images("Target issue", num_images=1)
    source_id = _create_incident_with_images("Source issue", num_images=2)

    source_reports = client.get(f"/api/photo-reports/{source_id}").json()
    assert len(source_reports) == 2
    evidence_ids = [r["evidence_id"] for r in source_reports]

    resp = client.post(
        f"/api/incidents/{target_id}/merge-photos",
        json={"evidence_ids": evidence_ids},
    )
    assert resp.status_code == 200
    assert resp.json()["merged_count"] == 2

    target_reports = client.get(f"/api/photo-reports/{target_id}").json()
    assert len(target_reports) == 3
    merged_ids = {r["evidence_id"] for r in target_reports}
    assert set(evidence_ids).issubset(merged_ids)

    source_after = client.get(f"/api/photo-reports/{source_id}").json()
    assert len(source_after) == 0

    incidents = client.get("/api/incidents").json()
    ids = {i["incident_id"] for i in incidents}
    assert source_id not in ids
    assert target_id in ids


def test_merge_photos_partial_merge_keeps_source_incident():
    target_id = _create_incident_with_images("Target", num_images=1)
    source_id = _create_incident_with_images("Source", num_images=2)
    reports = client.get(f"/api/photo-reports/{source_id}").json()
    one_ev = reports[0]["evidence_id"]

    resp = client.post(
        f"/api/incidents/{target_id}/merge-photos",
        json={"evidence_ids": [one_ev]},
    )
    assert resp.status_code == 200
    assert resp.json()["merged_count"] == 1

    assert len(client.get(f"/api/photo-reports/{source_id}").json()) == 1

    incidents = client.get("/api/incidents").json()
    ids = {i["incident_id"] for i in incidents}
    assert source_id in ids
    assert target_id in ids


def test_merge_photos_target_not_found_returns_404():
    source_id = _create_incident_with_images("Only source")
    ev = client.get(f"/api/photo-reports/{source_id}").json()[0]["evidence_id"]

    resp = client.post(
        "/api/incidents/nonexistent-target-id/merge-photos",
        json={"evidence_ids": [ev]},
    )
    assert resp.status_code == 404


def test_merge_photos_empty_list_returns_zero():
    target_id = _create_incident_with_images("Target")
    resp = client.post(
        f"/api/incidents/{target_id}/merge-photos",
        json={"evidence_ids": []},
    )
    assert resp.status_code == 200
    assert resp.json()["merged_count"] == 0


def test_merge_photos_skips_unknown_evidence_id():
    target_id = _create_incident_with_images("Target")
    resp = client.post(
        f"/api/incidents/{target_id}/merge-photos",
        json={"evidence_ids": ["deadbeefdeadbeefdeadbeefdeadbeef"]},
    )
    assert resp.status_code == 200
    assert resp.json()["merged_count"] == 0


def test_merge_photos_skips_row_already_on_target():
    target_id = _create_incident_with_images("Target", num_images=1)
    target_ev = client.get(f"/api/photo-reports/{target_id}").json()[0]["evidence_id"]

    resp = client.post(
        f"/api/incidents/{target_id}/merge-photos",
        json={"evidence_ids": [target_ev]},
    )
    assert resp.status_code == 200
    assert resp.json()["merged_count"] == 0


def test_merge_photos_sets_photo_report_discipline_from_target(db_session):
    target_id = _create_incident_with_images("Target", num_images=1)
    source_id = _create_incident_with_images("Source", num_images=1)

    _set_target_discipline(db_session, target_id, "ELECTRICAL")

    source_ev = client.get(f"/api/photo-reports/{source_id}").json()[0]["evidence_id"]
    _set_photo_discipline(db_session, source_ev, "BUILDINGS")

    resp = client.post(
        f"/api/incidents/{target_id}/merge-photos",
        json={"evidence_ids": [source_ev]},
    )
    assert resp.status_code == 200
    assert resp.json()["merged_count"] == 1

    target_reports = client.get(f"/api/photo-reports/{target_id}").json()
    merged = next(r for r in target_reports if r["evidence_id"] == source_ev)
    assert merged["photo_report_discipline"] == "ELECTRICAL"

    incidents = client.get("/api/incidents").json()
    assert source_id not in {i["incident_id"] for i in incidents}


def test_merge_photos_leaves_photo_discipline_unchanged_when_target_discipline_null(
    db_session,
):
    target_id = _create_incident_with_images("Target", num_images=1)
    source_id = _create_incident_with_images("Source", num_images=1)

    source_ev = client.get(f"/api/photo-reports/{source_id}").json()[0]["evidence_id"]
    _set_photo_discipline(db_session, source_ev, "MECHANICAL")

    resp = client.post(
        f"/api/incidents/{target_id}/merge-photos",
        json={"evidence_ids": [source_ev]},
    )
    assert resp.status_code == 200
    assert resp.json()["merged_count"] == 1

    target_reports = client.get(f"/api/photo-reports/{target_id}").json()
    merged = next(r for r in target_reports if r["evidence_id"] == source_ev)
    assert merged["photo_report_discipline"] == "MECHANICAL"

    incidents = client.get("/api/incidents").json()
    assert source_id not in {i["incident_id"] for i in incidents}
