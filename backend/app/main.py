"""Chalkproof FastAPI entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import export, lesson, pipeline, projects, qc

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

settings = get_settings()
app = FastAPI(title="Chalkproof", version="1.0.0", description="Local AI Lesson Creation Tool")

_origins = settings.cors_origin_list
# Allow all origins when "*" is configured (Vercel preview/prod frontends)
_allow_all = "*" in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _origins,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(pipeline.router)
app.include_router(lesson.router)
app.include_router(qc.router)
app.include_router(export.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    s = get_settings()
    return {
        "ok": True,
        "generator_model": s.generator_model,
        "qc_model": s.qc_model,
        "models_differ": s.generator_model != s.qc_model,
    }
