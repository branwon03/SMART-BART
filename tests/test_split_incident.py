"""Tests for POST /api/incidents/{incident_id}/split (split merged group into child incident)."""
import struct
import zlib

from fastapi.testclient import TestClient

from src.backend.database import Incident, PhotoReport
from src.backend.main import app
from tests.conftest import TestSession

client = TestClient(app)


def _tiny_png() -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = b"IHDR" + ihdr_data
    ihdr_chunk = (
        struct.pack(">I", len(ihdr_data))
        + ihdr
        + struct.pack(">I", zlib.crc32(ihdr) & 0xFFFFFFFF)
    )
    raw = zlib.compress(b"\x00\x00\x00\x00")
    idat = b"IDAT" + raw
    idat_chunk = (
        struct.pack(">I", len(raw))
        + idat
        + struct.pack(">I", zlib.crc32(idat) & 0xFFFFFFFF)
    )
    iend = b"IEND"
    iend_chunk = struct.pack(">I", 0) + iend + struct.pack(">I", zlib.crc32(iend) & 0xFFFFFFFF)
    return sig + ihdr_chunk + idat_chunk + iend_chunk


def _submission_with_npics(n_photos: int) -> tuple[str, list[str]]:
    png = _tiny_png()
    files = [
        ("media", (f"f{i}.png", png, "image/png"))
        for i in range(n_photos)
    ]
    resp = client.post(
        "/api/submissions",
        files=files if files else None,
        data={"description": "Parent context line"},
    )
    assert resp.status_code == 200, resp.text
    parent_id = resp.json()["incident_id"]
    reports = client.get(f"/api/photo-reports/{parent_id}").json()
    eids = sorted(r["evidence_id"] for r in reports)
    assert len(eids) == n_photos
    return parent_id, eids


def _set_parent_discipline(parent_id: str, discipline: str) -> None:
    db = TestSession()
    try:
        row = db.query(Incident).filter(Incident.incident_id == parent_id).first()
        assert row is not None
        row.discipline = discipline
        db.commit()
    finally:
        db.close()


def _mapping_evidence_to_incident(evidence_ids: list[str]) -> dict[str, str]:
    db = TestSession()
    try:
        rows = (
            db.query(PhotoReport)
            .filter(PhotoReport.evidence_id.in_(evidence_ids))
            .all()
        )
        return {r.evidence_id: r.incident_id for r in rows}
    finally:
        db.close()


def test_split_moves_one_photo_creates_child_with_title_and_shared_submission_id():
    parent_id, eids = _submission_with_npics(3)
    to_move = [eids[0]]

    resp = client.post(
        f"/api/incidents/{parent_id}/split",
        json={
            "evidence_ids": to_move,
            "title": "Child title from split",
            "discipline": "ELECTRICAL",
        },
    )
    assert resp.status_code == 200, resp.text
    child = resp.json()
    assert child["incident_id"] != parent_id
    assert child["vlm_summary"] == "Child title from split"
    assert child["discipline"] == "ELECTRICAL"

    parent_reports = client.get(f"/api/photo-reports/{parent_id}").json()
    child_reports = client.get(f"/api/photo-reports/{child['incident_id']}").json()
    assert len(parent_reports) == 2
    assert len(child_reports) == 1

    inv = _mapping_evidence_to_incident(eids)
    assert inv[eids[0]] == child["incident_id"]
    assert inv[eids[1]] == parent_id
    assert inv[eids[2]] == parent_id

    db = TestSession()
    try:
        moved = (
            db.query(PhotoReport)
            .filter(PhotoReport.evidence_id.in_(to_move))
            .all()
        )
        assert len(moved) == 1
        sid = moved[0].submission_id
        assert sid is not None and len(sid) == 32
    finally:
        db.close()


def test_split_moved_reports_share_same_submission_id_when_multiple_selected():
    parent_id, eids = _submission_with_npics(4)
    to_move = eids[:2]

    resp = client.post(
        f"/api/incidents/{parent_id}/split",
        json={"evidence_ids": to_move, "title": "Batch child"},
    )
    assert resp.status_code == 200
    child_id = resp.json()["incident_id"]

    db = TestSession()
    try:
        rows = (
            db.query(PhotoReport)
            .filter(PhotoReport.incident_id == child_id)
            .all()
        )
        assert len(rows) == 2
        sids = {r.submission_id for r in rows}
        assert len(sids) == 1
        assert next(iter(sids)) is not None
    finally:
        db.close()


def test_split_must_leave_parent_at_least_one_photo():
    parent_id, eids = _submission_with_npics(2)

    resp = client.post(
        f"/api/incidents/{parent_id}/split",
        json={"evidence_ids": eids, "title": "Would orphan parent"},
    )
    assert resp.status_code == 422


def test_split_unknown_evidence_id_returns_422():
    parent_id, eids = _submission_with_npics(2)

    resp = client.post(
        f"/api/incidents/{parent_id}/split",
        json={
            "evidence_ids": [eids[0], "ffffffffffffffffffffffffffffffff"],
            "title": "x",
        },
    )
    assert resp.status_code == 422


def test_split_duplicate_evidence_ids_counted_once_for_remaining_checks():
    parent_id, eids = _submission_with_npics(2)
    dup = [eids[0], eids[0]]

    resp = client.post(
        f"/api/incidents/{parent_id}/split",
        json={"evidence_ids": dup, "title": "Dedupped"},
    )
    assert resp.status_code == 200
    remaining = len(client.get(f"/api/photo-reports/{parent_id}").json())
    assert remaining == 1


def test_split_blank_title_returns_422():
    parent_id, eids = _submission_with_npics(2)

    resp = client.post(
        f"/api/incidents/{parent_id}/split",
        json={"evidence_ids": [eids[0]], "title": "   "},
    )
    assert resp.status_code == 422


def test_split_parent_not_found_returns_404():
    resp = client.post(
        "/api/incidents/no-such-incident/split",
        json={"evidence_ids": ["a"], "title": "t"},
    )
    assert resp.status_code == 404


def test_split_description_optional_updates_only_when_provided():
    parent_id, eids = _submission_with_npics(2)
    before_ctx = client.get(f"/api/photo-reports/{parent_id}").json()
    by_e = {r["evidence_id"]: r["user_context"] for r in before_ctx}

    r1 = client.post(
        f"/api/incidents/{parent_id}/split",
        json={"evidence_ids": [eids[0]], "title": "No desc key"},
    )
    assert r1.status_code == 200
    cid1 = r1.json()["incident_id"]
    moved1 = client.get(f"/api/photo-reports/{cid1}").json()[0]
    assert moved1["user_context"] == by_e[eids[0]]

    parent_id2, eids2 = _submission_with_npics(2)

    r2 = client.post(
        f"/api/incidents/{parent_id2}/split",
        json={
            "evidence_ids": [eids2[0]],
            "title": "With desc",
            "description": "New child narration",
        },
    )
    assert r2.status_code == 200
    moved2 = client.get(f"/api/photo-reports/{r2.json()['incident_id']}").json()[0]
    assert moved2["user_context"] == "New child narration"


def test_split_explicit_empty_description_clears_user_context():
    parent_id, eids = _submission_with_npics(2)

    resp = client.post(
        f"/api/incidents/{parent_id}/split",
        json={
            "evidence_ids": [eids[0]],
            "title": "T",
            "description": "",
        },
    )
    assert resp.status_code == 200
    child_ctx = (
        client.get(f"/api/photo-reports/{resp.json()['incident_id']}").json()[0][
            "user_context"
        ]
    )
    assert child_ctx == ""


def test_split_inherits_parent_discipline_when_discipline_field_omitted():
    parent_id, eids = _submission_with_npics(2)
    _set_parent_discipline(parent_id, "MECHANICAL")

    resp = client.post(
        f"/api/incidents/{parent_id}/split",
        json={"evidence_ids": [eids[0]], "title": "Inherited"},
    )
    assert resp.status_code == 200
    assert resp.json()["discipline"] == "MECHANICAL"


def test_split_child_priority_and_status_copied_from_parent():
    """PUT only updates priority/status; set via DB then split copies onto child."""
    parent_id, eids = _submission_with_npics(2)
    db = TestSession()
    try:
        row = db.query(Incident).filter(Incident.incident_id == parent_id).first()
        row.issue_priority = "Emergency"
        row.status = "In Progress"
        db.commit()
    finally:
        db.close()

    resp = client.post(
        f"/api/incidents/{parent_id}/split",
        json={"evidence_ids": [eids[0]], "title": "Cherry-picked"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["issue_priority"] == "Emergency"
    assert body["status"] == "In Progress"

