from __future__ import annotations

from datetime import datetime

import asyncpg


async def init_pool(database_url: str) -> asyncpg.Pool:
    """Create and return a connection pool."""
    return await asyncpg.create_pool(dsn=database_url)


async def close_pool(pool: asyncpg.Pool) -> None:
    """Gracefully close the connection pool."""
    await pool.close()


async def insert_submission(pool: asyncpg.Pool, submission: dict) -> dict:
    """Persist an inference result to the incidents table and echo the input."""
    await pool.execute(
        """
        INSERT INTO incidents (
            id, discipline, patron_description, num_images,
            inference_timestamp, status, priority, location
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        submission["submission_id"],
        submission["classification"],
        submission.get("description"),
        submission["num_images"],
        datetime.fromisoformat(submission["timestamp"]),
        "NEW",
        "UNSET",
        "UNASSIGNED",
    )
    return submission
