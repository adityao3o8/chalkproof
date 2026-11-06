#!/usr/bin/env python3
"""Run two end-to-end sample lessons and save outputs under /samples."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Make app importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlmodel import Session

from app.db import engine, init_db
from app.models.models import Project
from app.services.export import build_export_files, references_json
from app.services.pipeline import run_all
from app.services.generate import latest_lesson_version

SAMPLES = [
    {
        "slug": "http-requests-responses",
        "title": "HTTP Requests and Responses",
        "objective": (
            "Explain GET and POST methods and distinguish between "
            "2xx, 4xx, and 5xx response status categories."
        ),
    },
    {
        "slug": "http-caching-cache-control",
        "title": "HTTP Caching and Cache-Control Headers",
        "objective": (
            "Explain how Cache-Control directives (max-age, no-store, private, public) "
            "affect browser and shared caches, and identify common caching mistakes."
        ),
    },
]

OUT = Path(__file__).resolve().parents[2] / "samples"


async def run_one(slug: str, title: str, objective: str) -> None:
    init_db()
    with Session(engine) as session:
        project = Project(title=title, objective=objective, status="created")
        session.add(project)
        session.commit()
        session.refresh(project)
        pid = project.id
        assert pid

        print(f"\n=== Running sample: {title} (project {pid}) ===")
        result = await run_all(session, pid)
        print(json.dumps(result, indent=2, default=str))

        dest = OUT / slug
        dest.mkdir(parents=True, exist_ok=True)
        try:
            files = build_export_files(session, pid)
            for name, data in files.items():
                (dest / name).write_text(data, encoding="utf-8")
            (dest / "sources.json").write_text(
                json.dumps(references_json(session, pid), indent=2),
                encoding="utf-8",
            )
            lv = latest_lesson_version(session, pid)
            if lv:
                (dest / "lesson_content.json").write_text(
                    json.dumps(lv.content_json, indent=2),
                    encoding="utf-8",
                )
            print(f"Saved outputs to {dest}")
        except Exception as e:
            print(f"Export partial failure: {e}")
            (dest / "RUN_ERROR.txt").write_text(str(e) + "\n" + json.dumps(result, indent=2, default=str))


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for s in SAMPLES:
        await run_one(s["slug"], s["title"], s["objective"])
    print("\nDone. Fill samples/VERIFICATION.md with manual fact-checks.")


if __name__ == "__main__":
    asyncio.run(main())
