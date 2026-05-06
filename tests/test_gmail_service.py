"""
Gmail worker helpers + API: OAuth token lifecycle and gmail_thread_id on incidents.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.backend.main import app
from tests.test_png_bytes import _make_png_bytes

client = TestClient(app)


# ── get_service: auth / token persistence ─────────────────────────────────────


def test_get_service_returns_none_when_token_file_missing(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    monkeypatch.chdir(tmp_path)

    from src.backend.check_email import get_service

    assert get_service() is None


@patch("src.backend.check_email.build")
@patch("src.backend.check_email.Credentials.from_authorized_user_file")
def test_get_service_builds_gmail_client_when_token_valid(
    mock_from_file, mock_build, tmp_path, monkeypatch
):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "token.json").write_text("{}")
    monkeypatch.chdir(tmp_path)
    creds = MagicMock()
    creds.expired = False
    mock_from_file.return_value = creds
    mock_build.return_value = object()

    from src.backend.check_email import get_service

    svc = get_service()
    assert svc is mock_build.return_value
    mock_from_file.assert_called_once_with("config/token.json")
    mock_build.assert_called_once_with("gmail", "v1", credentials=creds)


@patch("src.backend.check_email.build")
@patch("google.auth.transport.requests.Request")
@patch("src.backend.check_email.Credentials.from_authorized_user_file")
def test_get_service_refreshes_expired_token_and_writes_file(
    mock_from_file, _mock_request_cls, mock_build, tmp_path, monkeypatch
):
    (tmp_path / "config").mkdir()
    token_path = tmp_path / "config" / "token.json"
    token_path.write_text('{"token": "old"}')
    monkeypatch.chdir(tmp_path)

    creds = MagicMock()
    creds.expired = True
    creds.refresh_token = "dummy-refresh"
    creds.to_json.return_value = '{"token": "new-refreshed", "refresh_token": "dummy-refresh"}'
    mock_from_file.return_value = creds
    mock_build.return_value = MagicMock()

    from src.backend.check_email import get_service

    get_service()
    creds.refresh.assert_called_once()
    assert '"new-refreshed"' in token_path.read_text()


@patch("src.backend.check_email.get_service")
def test_check_and_process_noop_when_unauthenticated(mock_get_service):
    mock_get_service.return_value = None

    from src.backend.check_email import check_and_process

    check_and_process()  # must not raise; no Gmail / HTTP calls
    mock_get_service.assert_called_once()


# ── submissions: gmail_thread_id stored and returned via /api/incidents ───────


def test_gmail_submission_persists_thread_id_on_incident():
    thread_id = "thread-abc-123"
    png = _make_png_bytes()
    resp = client.post(
        "/api/submissions",
        files=[("media", ("mail.png", png, "image/png"))],
        data={
            "description": "Photo from email snippet",
            "photo_location_id": "EMAIL-Unlocated",
            "gmail_thread_id": thread_id,
        },
    )
    assert resp.status_code == 200
    incident_id = resp.json()["incident_id"]

    rows = client.get("/api/incidents").json()
    match = [r for r in rows if r["incident_id"] == incident_id]
    assert len(match) == 1
    assert match[0]["gmail_thread_id"] == thread_id
