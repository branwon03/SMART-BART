"""
Prepopulate incidents + photo_reports using real images from scripts/seed_images/.

Reads image bytes from disk, stores as image_blob, inserts with status="New",
then runs each submission through the processor pipeline (Gemini classification
+ embedding + incident grouping).

Run from repo root:
  uv run python -m scripts.prepopulate

Docker:
  docker compose exec backend uv run python -m scripts.prepopulate

Uses DATABASE_URL from .env (see src.backend.database).

Host fix: `.env` often uses Postgres host `db` (Compose service name). That name
only resolves inside the stack. On laptop, script rewrites `db` -> `127.0.0.1`
before importing `src.backend.database` (unless `/.dockerenv` exists or
`PREPOPULATE_INSIDE_DOCKER=1`). Override entire URL with `PREPOPULATE_DATABASE_URL`.
Override host only with `PREPOPULATE_DB_HOST` (default `127.0.0.1`).
"""

from __future__ import annotations

import mimetypes
import os
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session

_UPROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = _UPROOT / ".env"
_SEED_DIR = Path(__file__).resolve().parent / "seed_images"


def _apply_prepopulate_database_url() -> None:
    """Set os.environ DATABASE_URL before src.backend.database creates engine."""
    load_dotenv(dotenv_path=_ENV_FILE)
    override = os.getenv("PREPOPULATE_DATABASE_URL")
    if override:
        os.environ["DATABASE_URL"] = override
        return

    raw = os.getenv("DATABASE_URL")
    if not raw:
        raise RuntimeError(
            "DATABASE_URL is not set (check .env or set PREPOPULATE_DATABASE_URL)"
        )

    url = make_url(raw)
    if url.drivername.startswith("sqlite"):
        return

    inside_docker = Path("/.dockerenv").is_file() or os.getenv(
        "PREPOPULATE_INSIDE_DOCKER", ""
    ).lower() in ("1", "true", "yes")

    if url.host == "db" and not inside_docker:
        host = os.getenv("PREPOPULATE_DB_HOST", "127.0.0.1")
        new_url = url.set(host=host)
        os.environ["DATABASE_URL"] = new_url.render_as_string(hide_password=False)
        print(
            f"[prepopulate] DATABASE_URL host db -> {host} "
            f"(run on host; inside container this skip auto)"
        )


_apply_prepopulate_database_url()

from src.backend.database import (  # noqa: E402
    Base,
    Incident,
    PhotoReport,
    SessionLocal,
    engine,
    ensure_image_blob_columns_on_photo_reports,
    ensure_reporter_columns_on_photo_reports,
    init_db,
)
from src.backend.gps_lookup import BART_STATIONS  # noqa: E402
from src.backend.processor import process_submission  # noqa: E402

SEED_REPORTER_NAME = "Seed User"


@dataclass(frozen=True)
class _SeedIncident:
    description: str
    images: tuple[str, ...] = ()


SEED_INCIDENTS: list[_SeedIncident] = [
    _SeedIncident(
        description="Pizza boxes left outside recycling station",
        images=("1-trashA.jpg", "2-trashA.jpg"),
    ),
    _SeedIncident(
        description="Trash overflowing onto ground near lawn area",
        images=("4-trashB.jpg", "5-trashB.jpg"),
    ),
    _SeedIncident(
        description="Blue light phone appears sun-bleached and worn",
        images=("7-phoneA.jpg", "8-phoneA.jpg"),
    ),
    _SeedIncident(
        description="Emergency phone unit 48 showing wear on panel",
        images=("10-phoneB.jpg", "11-phoneB.jpg"),
    ),
    _SeedIncident(
        description="Outdoor GFCI outlet cover hanging open near walkway",
        images=("16-outletA.jpg", "17-outletA.jpg"),
    ),
    _SeedIncident(
        description="Standard outlet near baseboard, plate slightly loose",
        images=("19-outletB.jpg", "20-outletB.jpg"),
    ),
]


def _random_recent_utc() -> datetime:
    now = datetime.now(timezone.utc)
    delta = timedelta(days=random.uniform(0.0, 7.0))
    return now - delta


def _seed_already_present(db: Session) -> bool:
    return (
        db.query(PhotoReport)
        .filter(PhotoReport.reporter_name == SEED_REPORTER_NAME)
        .first()
        is not None
    )


def _read_image(filename: str) -> tuple[bytes, str]:
    """Read image bytes and detect MIME type from seed_images/."""
    path = _SEED_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Seed image not found: {path}")
    mime, _ = mimetypes.guess_type(str(path))
    if mime is None:
        mime = "image/jpeg"
    return path.read_bytes(), mime


def prepopulate() -> None:
    from sqlalchemy import text

    if not _SEED_DIR.is_dir():
        raise RuntimeError(f"Seed images directory missing: {_SEED_DIR}")

    init_db()

    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
    except Exception:
        pass

    Base.metadata.create_all(bind=engine)
    ensure_reporter_columns_on_photo_reports()
    ensure_image_blob_columns_on_photo_reports()

    db = SessionLocal()
    try:
        if _seed_already_present(db):
            print(
                f"[prepopulate] Skip: already have rows with "
                f"reporter_name={SEED_REPORTER_NAME!r}."
            )
            return

        station_names = list(BART_STATIONS.keys())
        if not station_names:
            raise RuntimeError("BART_STATIONS is empty; cannot assign location.")

        submission_ids: list[str] = []

        for spec in SEED_INCIDENTS:
            incident_id = uuid.uuid4().hex
            submission_id = uuid.uuid4().hex
            location_id = random.choice(station_names)
            created_at = _random_recent_utc()

            incident = Incident(
                incident_id=incident_id,
                status="New",
                issue_priority=None,
                discipline=None,
                vlm_summary=spec.description,
                location_id=location_id,
                created_at=created_at,
                gmail_thread_id=None,
            )
            db.add(incident)

            for filename in spec.images:
                blob, mime = _read_image(filename)
                evidence_id = uuid.uuid4().hex

                photo = PhotoReport(
                    evidence_id=evidence_id,
                    incident_id=incident_id,
                    submission_id=submission_id,
                    image_url=f"/api/images/{evidence_id}",
                    image_blob=blob,
                    image_mime=mime,
                    embedding=None,
                    submitted_at=created_at,
                    user_context=spec.description,
                    found_priority=None,
                    vlm_summary=None,
                    photo_report_status="New",
                    photo_report_confidence=None,
                    photo_report_discipline=None,
                    photo_location_id=location_id,
                    reporter_name=SEED_REPORTER_NAME,
                    reporter_contact=None,
                )
                db.add(photo)
                print(
                    f"[prepopulate] + incident={incident_id[:8]}… "
                    f"photo={evidence_id[:8]}… file={filename} ({len(blob)} bytes)"
                )

            db.commit()
            submission_ids.append(submission_id)

        print(
            f"\n[prepopulate] Inserted {len(SEED_INCIDENTS)} incidents. "
            f"Running processor on each submission...\n"
        )

        for sid in submission_ids:
            print(f"[prepopulate] >>> Processing submission {sid[:8]}…")
            process_submission(sid, db)

        print(
            f"\n[prepopulate] Done. {len(SEED_INCIDENTS)} submissions "
            f"processed via Gemini."
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    prepopulate()
