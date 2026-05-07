"""Expose the FastAPI app at module level for Vercel detection (see repo root deployment)."""

import src.backend.main as backend

app = backend.app
