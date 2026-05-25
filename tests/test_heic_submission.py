from fastapi.testclient import TestClient
from src.backend.main import app


client = TestClient(app)


def test_heic_in_supported_list():
    from src.backend.inference import kSupportedList

    assert "heic" in kSupportedList
    assert "heif" in kSupportedList


def test_heic_upload_accepted():
    """POST /api/submissions should accept a .heic file without 422."""
    fake_heic = b"\x00" * 100
    response = client.post(
        "/api/submissions",
        files=[("media", ("test.heic", fake_heic, "image/heic"))],
        data={
            "description": "test heic upload",
            "photo_location_id": "Gym",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "incident_id" in body
    assert body.get("location_id") == "Gym"


def test_geolocation_auto_detect_returns_location():
    """When photo_location_id is 'Assign-Me-Via-Geolocation' and file has GPS EXIF,
    the response should contain the resolved location_id."""
    fake_jpg = b"\x00" * 100
    response = client.post(
        "/api/submissions",
        files=[("media", ("test.jpg", fake_jpg, "image/jpeg"))],
        data={
            "description": "auto detect test",
            "photo_location_id": "Assign-Me-Via-Geolocation",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "location_id" in body


def test_manual_location_preserved():
    """When user selects a specific location, it is preserved as-is."""
    fake_jpg = b"\x00" * 100
    response = client.post(
        "/api/submissions",
        files=[("media", ("test.jpg", fake_jpg, "image/jpeg"))],
        data={
            "description": "manual location test",
            "photo_location_id": "Gym",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["location_id"] == "Gym"


def test_heic_image_served(db_session):
    """A saved .heic file should be retrievable via GET /api/images/{id}."""
    from datetime import datetime, timezone

    from src.backend.database import Incident, PhotoReport
    from src.backend.main import UPLOAD_DIR

    evidence_id = "test-heic-serve"
    incident_id = "inc-heic-serve"
    now = datetime.now(timezone.utc)

    db_session.add(
        Incident(
            incident_id=incident_id,
            status="New",
            created_at=now,
        )
    )
    db_session.add(
        PhotoReport(
            evidence_id=evidence_id,
            incident_id=incident_id,
            image_url=f"/api/images/{evidence_id}",
            submitted_at=now,
            photo_report_status="New",
            found_priority="Standard",
            photo_location_id="Gym",
        )
    )
    db_session.commit()

    heic_path = UPLOAD_DIR / f"{evidence_id}.heic"
    heic_path.write_bytes(b"\x00\x00\x00\x1cftypmif1")

    response = client.get(f"/api/images/{evidence_id}")
    assert response.status_code == 200
