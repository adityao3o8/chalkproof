"""Vercel serverless entrypoint for the FastAPI app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make backend/app importable on Vercel
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Serverless-friendly defaults (ephemeral disk under /tmp)
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/chalkproof.db")
os.environ.setdefault(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,*",
)

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402

# Ensure tables exist on cold start (startup hooks are unreliable in serverless)
init_db()

# Vercel Python runtime expects an ASGI `app`
__all__ = ["app"]
