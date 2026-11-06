"""Lesson generation with claim ledger and time-budget enforcement."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models.models import Claim, LessonVersion, Source
from app.models.schemas import LessonBlock, LessonClaim, LessonContent, KnowledgeCheckItem
from app.services.llm import json_completion
from app.utils.time_budget import validate_or_rebalance

logger = logging.getLogger(__name__)


class LLMLessonOut(BaseModel):
    """Schema the generator model must return."""

    blocks: list[LessonBlock]
    claims: list[LessonClaim] = Field(default_factory=list)
    knowledge_checks: list[KnowledgeCheckItem] = Field(default_factory=list)
    total_estimated_minutes: float = 45.0


SYSTEM_PROMPT = """You are an expert instructional designer creating a 45-minute lesson.
You MUST return ONLY valid JSON. Never refuse. Never apologize. Never write prose outside JSON.
If sources are weak or off-topic, still create a solid lesson from the title + learning objective,
use whatever relevant source text exists for claims, and leave claims=[] only when no quote fits.

JSON schema:
{
  "blocks": [{"id": "b1", "type": "...", "title": "...", "content": "...", "estimated_minutes": N}],
  "claims": [{"claim_text": "...", "source_id": <int from provided source list>, "supporting_quote": "...", "block_id": "b1"}],
  "knowledge_checks": [{"question": "...", "answer": "...", "explanation": "..."}],
  "total_estimated_minutes": 45
}

Required block types (use these type values), in order:
1. hook — engaging intro
2. concept — core concept explanations (you may include 2-3 concept blocks)
3. worked_example — worked examples
4. practical — Practical Applications with 2-3 real-world scenarios
5. activity — hands-on activity
6. knowledge_check — questions (also populate knowledge_checks array)
7. summary — concise wrap-up
8. videos — supplementary videos with why-watch + timestamp (use provided video sources if any)
9. references — list available source links; if few sources, say so honestly

Rules:
- Total estimated_minutes across blocks MUST be 45 (+/- 2).
- Write in ORIGINAL wording. Never copy source text verbatim into block content.
- For factual claims you can ground: supporting_quote must be EXACT substring of that source's TEXT.
- Use only source_id values from the provided list.
- Knowledge checks must test the learning objective.
- Output must start with { and end with }.
"""


def _sources_for_prompt(sources: list[Source]) -> str:
    parts = []
    for s in sources:
        parts.append(
            f"[source_id={s.id}] type={s.type} tier={s.reliability_tier} "
            f"title={s.title!r} url={s.url}\n"
            f"relevant_segment={s.relevant_segment}\n"
            f"TEXT:\n{(s.fetched_text or '')[:4000]}\n---"
        )
    return "\n".join(parts)


def _use_demo(title: str, objective: str) -> bool:
    from app.config import get_settings

    s = get_settings()
    if s.chalkproof_demo_mode:
        return True
    # Auto-demo when no provider keys are configured
    if not s.has_llm_keys:
        return True
    return False


async def run_generate(
    session: Session,
    project_id: int,
    title: str,
    objective: str,
) -> LessonContent:
    sources = session.exec(select(Source).where(Source.project_id == project_id)).all()
    if not sources:
        raise RuntimeError("No sources available — run research first")

    if _use_demo(title, objective):
        from app.services.demo_fixture import build_fixture

        logger.info("Using demo fixture lesson (no LLM keys / CHALKPROOF_DEMO_MODE)")
        content = build_fixture(title, objective, [s.id for s in sources if s.id is not None])
        # Attach real quotes from fetched MDN text when possible
        for c in content.claims:
            src = next((s for s in sources if s.id == c.source_id), None)
            if src and src.fetched_text and c.supporting_quote not in src.fetched_text:
                # Find a short sentence from the source as a real quote
                snippet = (src.fetched_text or "").strip().split(".")[0][:180]
                if snippet:
                    c.supporting_quote = snippet
    else:
        user = (
            f"Lesson title: {title}\nLearning objective: {objective}\n\n"
            f"SOURCES:\n{_sources_for_prompt(sources)}\n\n"
            "Create the full 45-minute lesson JSON now."
        )
        raw = await json_completion("generator", SYSTEM_PROMPT, user, LLMLessonOut)
        content = LessonContent(
            title=title,
            objective=objective,
            blocks=raw.blocks,
            claims=raw.claims,
            knowledge_checks=raw.knowledge_checks,
            total_estimated_minutes=raw.total_estimated_minutes,
        )

    content, rebalanced = validate_or_rebalance(content)
    if rebalanced:
        logger.info("Lesson time budget rebalanced to %s minutes", content.total_estimated_minutes)

    # Next version number
    existing = session.exec(
        select(LessonVersion).where(LessonVersion.project_id == project_id)
    ).all()
    next_ver = (max((v.version for v in existing), default=0) + 1)

    lv = LessonVersion(
        project_id=project_id,
        version=next_ver,
        content_json=content.model_dump(),
        author="ai",
        note="AI generation",
    )
    session.add(lv)
    session.commit()
    session.refresh(lv)

    # Persist claims linked to this version
    for old in session.exec(select(Claim).where(Claim.lesson_version_id == lv.id)).all():
        session.delete(old)
    valid_ids = {s.id for s in sources}
    for c in content.claims:
        sid = c.source_id if c.source_id in valid_ids else None
        session.add(
            Claim(
                lesson_version_id=lv.id,
                block_id=c.block_id,
                claim_text=c.claim_text,
                source_id=sid,
                supporting_quote=c.supporting_quote,
            )
        )
    session.commit()
    return content


def latest_lesson_version(session: Session, project_id: int) -> LessonVersion | None:
    versions = session.exec(
        select(LessonVersion).where(LessonVersion.project_id == project_id)
    ).all()
    if not versions:
        return None
    return max(versions, key=lambda v: v.version)


def save_instructor_version(
    session: Session,
    project_id: int,
    content: LessonContent,
    note: str = "manual save",
) -> LessonVersion:
    existing = session.exec(
        select(LessonVersion).where(LessonVersion.project_id == project_id)
    ).all()
    next_ver = (max((v.version for v in existing), default=0) + 1)
    lv = LessonVersion(
        project_id=project_id,
        version=next_ver,
        content_json=content.model_dump(),
        author="instructor",
        note=note,
    )
    session.add(lv)
    session.commit()
    session.refresh(lv)

    # Copy claims forward if present in content
    for c in content.claims:
        session.add(
            Claim(
                lesson_version_id=lv.id,
                block_id=c.block_id,
                claim_text=c.claim_text,
                source_id=c.source_id,
                supporting_quote=c.supporting_quote,
            )
        )
    session.commit()
    return lv
