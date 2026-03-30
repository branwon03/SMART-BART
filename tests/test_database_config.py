from src.backend import database


def test_get_database_url_normalizes_neon_url(monkeypatch):
    neon_url = (
        "postgresql://user:secret@ep-example-pooler.us-east-2.aws.neon.tech/"
        "neondb?sslmode=require&channel_binding=require"
    )
    monkeypatch.setenv("DATABASE_URL", neon_url)

    assert database.get_database_url() == (
        "postgresql+psycopg://user:secret@ep-example-pooler.us-east-2.aws.neon.tech/"
        "neondb?sslmode=require&channel_binding=require"
    )


def test_get_database_url_uses_safe_local_default(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert database.get_database_url() == (
        "postgresql+psycopg://postgres:CSE_312!@db:5432/bart_db"
    )
