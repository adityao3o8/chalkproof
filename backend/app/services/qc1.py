"""QC Layer 1 — Research & Factual Accuracy (independent of QC2)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models.models import Claim, LessonVersion, QCReport, Source
from app.models.schemas import LessonContent, QCIssue
from app.services.generate import latest_lesson_version
from app.services.llm import json_completion
from app.utils.plagiarism import check_passage_against_sources, suggest_rewrite_hint
from app.utils.quote_match import quote_in_source

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are QC Layer 1: Research & Factual Accuracy auditor.
You do NOT evaluate instructional quality — only facts, sources, and grounding.
Return JSON:
{
  "summary": "short overall assessment",
  "score": 0-100,
  "issues": [
    {
      "id": "qc1-1",
      "severity": "high"|"med"|"low",
      "location_block_id": "b1 or null",
      "description": "...",
      "evidence": "...",
      "suggested_fix": "concrete replacement text or empty",
      "category": "unsupported_claim|misleading|contradiction|low_reliability|irrelevant_source|gap|inconsistency|plagiarism|executable"
    }
  ]
}

Flag: unsupported/misleading claims, contradictions, low-reliability reliance,
irrelevant sources, gaps/inconsistencies between blocks.
For each claim, judge whether the supporting_quote semantically supports the claim_text.
"""


class QC1LLMOut(BaseModel):
    summary: str = ""
    score: float = 50.0
    issues: list[QCIssue] = Field(default_factory=list)


def _programmatic_checks(
    session: Session,
    lesson_version_id: int,
    content: LessonContent,
) -> list[QCIssue]:
    issues: list[QCIssue] = []
    claims = session.exec(
        select(Claim).where(Claim.lesson_version_id == lesson_version_id)
    ).all()
    sources: dict[int, Source] = {}
    for c in claims:
        if c.source_id and c.source_id not in sources:
            src_row = session.get(Source, c.source_id)
            if src_row and src_row.id is not None:
                sources[src_row.id] = src_row
    all_sources: list[Source] = []

    for c in claims:
        src = sources.get(c.source_id) if c.source_id else None
        if not src:
            issues.append(
                QCIssue(
                    id=f"qc1-prog-{uuid.uuid4().hex[:8]}",
                    severity="high",
                    location_block_id=c.block_id,
                    description=f"Claim has no linked source: {c.claim_text[:120]}",
                    evidence="source_id missing or invalid",
                    suggested_fix="Attach a valid source or remove the unsupported claim.",
                    category="unsupported_claim",
                )
            )
            continue
        matched, method = quote_in_source(c.supporting_quote, src.fetched_text or "")
        if not matched:
            issues.append(
                QCIssue(
                    id=f"qc1-prog-{uuid.uuid4().hex[:8]}",
                    severity="high",
                    location_block_id=c.block_id,
                    description=f"Supporting quote not found in source text for claim: {c.claim_text[:100]}",
                    evidence=f"quote={c.supporting_quote[:200]!r} source_id={src.id}",
                    suggested_fix="Replace with a quote that appears verbatim in the source, or revise the claim.",
                    category="unsupported_claim",
                )
            )
        if src.reliability_tier == "low":
            issues.append(
                QCIssue(
                    id=f"qc1-prog-{uuid.uuid4().hex[:8]}",
                    severity="med",
                    location_block_id=c.block_id,
                    description=f"Claim relies on low-reliability source: {src.title}",
                    evidence=src.url,
                    suggested_fix="Prefer an official docs/RFC/MDN source for this claim.",
                    category="low_reliability",
                )
            )

    # Plagiarism n-gram check on all blocks
    lv_row = session.get(LessonVersion, lesson_version_id)
    project_id = lv_row.project_id if lv_row else None
    if project_id:
        all_sources = list(session.exec(select(Source).where(Source.project_id == project_id)).all())
    src_pairs = [(s.id, s.fetched_text or "") for s in all_sources]
    for b in content.blocks:
        findings = check_passage_against_sources(b.content, src_pairs, n=8)
        for f in findings:
            issues.append(
                QCIssue(
                    id=f"qc1-plag-{uuid.uuid4().hex[:8]}",
                    severity="high",
                    location_block_id=b.id,
                    description=f"Possible plagiarism: >8 consecutive matching words vs source {f['source_id']}",
                    evidence=f["matched_phrase"],
                    suggested_fix=suggest_rewrite_hint(f["matched_phrase"]),
                    category="plagiarism",
                )
            )

    # Executable example flags
    ex = content.executable_examples
    if ex and ex.get("applicable") and ex.get("status") == "failed":
        issues.append(
            QCIssue(
                id=f"qc1-exec-{uuid.uuid4().hex[:8]}",
                severity="med",
                location_block_id=None,
                description="One or more executable examples failed in the sandbox",
                evidence=ex.get("message", ""),
                suggested_fix="Re-run executable examples or remove failed demos from the lesson.",
                category="executable",
            )
        )

    # Unverified videos note
    for s in all_sources:
        if s.type == "video" and not s.video_verified:
            issues.append(
                QCIssue(
                    id=f"qc1-vid-{uuid.uuid4().hex[:8]}",
                    severity="low",
                    location_block_id=None,
                    description=f"Video source unverified (no transcript): {s.title}",
                    evidence=s.url,
                    suggested_fix="Mark as optional or replace with a transcript-verified video.",
                    category="irrelevant_source",
                )
            )

    return issues


async def run_qc1(session: Session, project_id: int) -> QCReport:
    lv = latest_lesson_version(session, project_id)
    if not lv:
        raise RuntimeError("No lesson version — run generate first")

    content = LessonContent.model_validate(lv.content_json)
    sources = session.exec(select(Source).where(Source.project_id == project_id)).all()
    claims = session.exec(select(Claim).where(Claim.lesson_version_id == lv.id)).all()

    prog_issues = _programmatic_checks(session, lv.id, content)

    # LLM semantic audit (independent — does not see QC2)
    claims_blob = "\n".join(
        f"- claim={c.claim_text!r} quote={c.supporting_quote!r} source_id={c.source_id} block={c.block_id}"
        for c in claims
    )
    sources_blob = "\n".join(
        f"[{s.id}] tier={s.reliability_tier} type={s.type} title={s.title} url={s.url}\n{(s.fetched_text or '')[:1500]}"
        for s in sources
    )
    blocks_blob = "\n".join(f"[{b.id}/{b.type}] {b.title}: {b.content[:500]}" for b in content.blocks)

    user = (
        f"Audit this lesson for factual accuracy.\n\nCLAIMS:\n{claims_blob}\n\n"
        f"SOURCES:\n{sources_blob}\n\nBLOCKS:\n{blocks_blob}\n"
        f"Research notes / degradations: {len(sources)} sources collected."
    )

    from app.config import get_settings

    settings = get_settings()
    has_keys = bool(settings.openai_api_key or settings.anthropic_api_key or settings.google_api_key)
    if settings.chalkproof_demo_mode or not has_keys:
        llm_issues = []
        summary = (
            "Demo/programmatic QC1 only (no LLM keys). "
            f"Found {len(prog_issues)} programmatic issue(s)."
        )
        score = max(0.0, 90.0 - 8.0 * len([i for i in prog_issues if i.severity == "high"]))
    else:
        try:
            llm_out = await json_completion("qc", SYSTEM_PROMPT, user, QC1LLMOut)
            llm_issues = llm_out.issues
            summary = llm_out.summary
            score = llm_out.score
        except Exception as e:
            logger.warning("QC1 LLM failed, using programmatic only: %s", e)
            llm_issues = []
            summary = f"LLM audit unavailable ({e}); programmatic checks only."
            score = max(0, 80 - 10 * len(prog_issues))

    # Merge — programmatic first
    all_issues = prog_issues + llm_issues
    # Ensure ids unique
    for i, issue in enumerate(all_issues):
        if not issue.id:
            issue.id = f"qc1-{i+1}"

    report = QCReport(
        project_id=project_id,
        layer=1,
        lesson_version_id=lv.id,
        issues_json=[iss.model_dump() for iss in all_issues],
        summary=summary,
        score=score,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report
