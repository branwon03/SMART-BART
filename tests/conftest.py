"""
Shared test fixtures.

Swaps the production Postgres engine for an in-memory SQLite so tests run
without Docker / a live database.  Redirects image uploads to a temp directory.
"""
import os

# CI and fresh clones may not have .env; database.py requires a URL at import time.
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.backend.database import Base, get_db
import src.backend.main as _main_module
from src.backend.main import app

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def db_session(_reset_tables_and_uploads):
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _reset_tables_and_uploads(tmp_path):
    """Create tables + temp upload dir before each test, tear down after."""
    _orig = _main_module.UPLOAD_DIR
    _main_module.UPLOAD_DIR = tmp_path / "uploads"
    _main_module.UPLOAD_DIR.mkdir()

    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)

    _main_module.UPLOAD_DIR = _orig
