from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.database.db import close_pool, init_pool, insert_submission


SAMPLE_SUBMISSION = {
    "submission_id": "abc123",
    "classification": "ELECTRICAL",
    "description": "Exposed wiring near platform edge",
    "num_images": 1,
    "timestamp": datetime(2026, 1, 1, 12, 0, 0).isoformat(),
}


@pytest.mark.asyncio
async def test_insert_submission_echoes_input():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")

    result = await insert_submission(pool, SAMPLE_SUBMISSION)

    assert result == SAMPLE_SUBMISSION


@pytest.mark.asyncio
async def test_insert_submission_none_description():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    submission = {
        "submission_id": "def456",
        "classification": "GROUNDS",
        "description": None,
        "num_images": 0,
        "timestamp": datetime(2026, 1, 1, 12, 0, 0).isoformat(),
    }

    result = await insert_submission(pool, submission)

    assert result == submission
    assert result["description"] is None


@pytest.mark.asyncio
async def test_pool_lifecycle(monkeypatch):
    fake_pool = AsyncMock()

    async def _fake_create_pool(*args, **kwargs):
        return fake_pool

    monkeypatch.setattr("src.database.db.asyncpg.create_pool", _fake_create_pool)

    pool = await init_pool("postgresql://fake:fake@localhost/fake")
    assert pool is fake_pool

    await close_pool(pool)
    fake_pool.close.assert_awaited_once()
