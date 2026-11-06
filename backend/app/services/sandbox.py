"""Executable examples sandbox — real HTTP requests for HTTP/code demos."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from sqlmodel import Session

from app.models.schemas import LessonContent
from app.services.generate import latest_lesson_version, save_instructor_version

logger = logging.getLogger(__name__)

HTTP_TOPIC_HINTS = re.compile(
    r"\b(http|https|get|post|request|response|status|header|api|rest|fetch)\b",
    re.I,
)


async def _run_httpbin_demos() -> list[dict[str, Any]]:
    demos = []
    cases = [
        ("GET", "https://httpbin.org/get", None),
        ("POST", "https://httpbin.org/post", {"lesson": "chalkproof", "method": "POST"}),
        ("STATUS_200", "https://httpbin.org/status/200", None),
        ("STATUS_404", "https://httpbin.org/status/404", None),
        ("STATUS_500", "https://httpbin.org/status/500", None),
    ]
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for name, url, body in cases:
            try:
                if body is not None:
                    resp = await client.post(url, json=body)
                else:
                    resp = await client.get(url)
                demos.append(
                    {
                        "name": name,
                        "url": url,
                        "ok": True,
                        "status_code": resp.status_code,
                        "headers": dict(list(resp.headers.items())[:12]),
                        "body_preview": resp.text[:500],
                        "error": None,
                    }
                )
            except Exception as e:
                demos.append(
                    {
                        "name": name,
                        "url": url,
                        "ok": False,
                        "status_code": None,
                        "headers": {},
                        "body_preview": "",
                        "error": str(e),
                    }
                )
    return demos


def _topic_is_http(title: str, objective: str, content: LessonContent) -> bool:
    blob = f"{title} {objective} " + " ".join(b.content for b in content.blocks)
    return bool(HTTP_TOPIC_HINTS.search(blob))


async def run_executable_examples(
    session: Session,
    project_id: int,
    title: str,
    objective: str,
) -> dict[str, Any]:
    lv = latest_lesson_version(session, project_id)
    if not lv:
        raise RuntimeError("No lesson version — run generate first")

    content = LessonContent.model_validate(lv.content_json)
    if not _topic_is_http(title, objective, content):
        result = {
            "applicable": False,
            "status": "not_applicable",
            "message": "Topic has no runnable HTTP/code examples",
            "demos": [],
        }
        content.executable_examples = result
        save_instructor_version(session, project_id, content, note="executable examples N/A")
        return result

    demos = await _run_httpbin_demos()
    # Embed a short appendix block into worked examples if present
    summary_lines = []
    for d in demos:
        if d["ok"]:
            summary_lines.append(
                f"- {d['name']}: status={d['status_code']} body={d['body_preview'][:80]!r}"
            )
        else:
            summary_lines.append(f"- {d['name']}: FAILED — {d['error']}")

    embed = (
        "\n\n### Live sandbox outputs (httpbin.org)\n"
        + "\n".join(summary_lines)
    )
    for b in content.blocks:
        if b.type == "worked_example":
            if "Live sandbox outputs" not in b.content:
                b.content = b.content + embed
            break

    failed = [d for d in demos if not d["ok"]]
    result = {
        "applicable": True,
        "status": "failed" if failed else "ok",
        "message": f"{len(demos) - len(failed)}/{len(demos)} demos succeeded",
        "demos": demos,
    }
    content.executable_examples = result
    save_instructor_version(session, project_id, content, note="executable examples embedded")
    return result
