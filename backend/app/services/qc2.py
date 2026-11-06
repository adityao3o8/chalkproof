"""QC Layer 2 — Instructional Quality (independent of QC1; never sees QC1 output)."""

from __future__ import annotations

import logging
import uuid

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.models.models import QCReport
from app.models.schemas import LessonContent, QCIssue
from app.services.generate import latest_lesson_version
from app.services.llm import json_completion
from app.services.student_simulator import run_student_simulator
from app.utils.time_budget import TARGET_MINUTES, TOLERANCE

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are QC Layer 2: Instructional Quality auditor.
You do NOT evaluate source grounding or factual citation — only teaching quality.
Return JSON:
{
  "summary": "short overall assessment",
  "score": 0-100,
  "issues": [
    {
      "id": "qc2-1",
      "severity": "high"|"med"|"low",
      "location_block_id": "b1 or null",
      "description": "...",
      "evidence": "...",
      "suggested_fix": "concrete improved text",
      "category": "objective_alignment|clarity|structure|relevance|gap_explanation|gap_examples|gap_practical|time_budget|knowledge_check|student_simulator"
    }
  ]
}

Evaluate:
- Objective alignment per block
- Clarity, structure, relevance
- Gaps in explanations, examples, and practical applications (separate findings)
- Whether knowledge checks actually test the learning objective
"""


class QC2LLMOut(BaseModel):
    summary: str = ""
    score: float = 50.0
    issues: list[QCIssue] = Field(default_factory=list)


def _time_budget_issues(content: LessonContent) -> list[QCIssue]:
    total = content.recomputed_minutes()
    issues: list[QCIssue] = []
    if abs(total - TARGET_MINUTES) > TOLERANCE:
        kind = "overload" if total > TARGET_MINUTES else "underload"
        issues.append(
            QCIssue(
                id=f"qc2-time-{uuid.uuid4().hex[:8]}",
                severity="med",
                location_block_id=None,
                description=f"Time budget {kind}: blocks sum to {total} min (target {TARGET_MINUTES} ±{TOLERANCE})",
                evidence=f"per-block: " + ", ".join(f"{b.id}={b.estimated_minutes}" for b in content.blocks),
                suggested_fix=f"Adjust block minutes so they sum to {TARGET_MINUTES}.",
                category="time_budget",
            )
        )
    return issues


async def run_qc2(session: Session, project_id: int) -> QCReport:
    lv = latest_lesson_version(session, project_id)
    if not lv:
        raise RuntimeError("No lesson version — run generate first")

    content = LessonContent.model_validate(lv.content_json)
    prog_issues = _time_budget_issues(content)

    blocks_blob = "\n\n".join(
        f"[{b.id}] type={b.type} title={b.title} minutes={b.estimated_minutes}\n{b.content}"
        for b in content.blocks
    )
    kc_blob = "\n".join(
        f"Q: {k.question}\nA: {k.answer}\nWhy: {k.explanation}" for k in content.knowledge_checks
    )
    user = (
        f"Lesson title: {content.title}\nLearning objective: {content.objective}\n\n"
        f"BLOCKS:\n{blocks_blob}\n\nKNOWLEDGE CHECKS:\n{kc_blob}\n\n"
        f"Total minutes: {content.recomputed_minutes()}"
    )

    from app.config import get_settings

    settings = get_settings()
    has_keys = bool(settings.openai_api_key or settings.anthropic_api_key or settings.google_api_key)
    demo = settings.chalkproof_demo_mode or not has_keys

    if demo:
        llm_issues = [
            QCIssue(
                id=f"qc2-demo-{uuid.uuid4().hex[:8]}",
                severity="low",
                location_block_id="b2",
                description="Demo mode: add one more concrete analogy for GET vs POST for novices.",
                evidence="Instructional polish suggestion (demo)",
                suggested_fix=(
                    "Analogy: GET is like reading a library book in place; "
                    "POST is like handing the librarian a filled-out form to process."
                ),
                category="clarity",
            )
        ]
        summary = "Demo QC2 (no LLM keys): time-budget + sample instructional suggestion."
        score = 82.0
        sim_issues: list[QCIssue] = []
    else:
        try:
            llm_out = await json_completion("qc", SYSTEM_PROMPT, user, QC2LLMOut)
            llm_issues = llm_out.issues
            summary = llm_out.summary
            score = llm_out.score
        except Exception as e:
            logger.warning("QC2 LLM failed: %s", e)
            llm_issues = []
            summary = f"LLM instructional audit unavailable ({e}); time-budget checks only."
            score = 70.0

        # Student simulator — separate LLM call; Phase 2 differentiator
        sim_issues = []
        try:
            sim_issues = await run_student_simulator(content)
        except Exception as e:
            logger.warning("Student simulator failed: %s", e)
            sim_issues.append(
                QCIssue(
                    id=f"qc2-sim-{uuid.uuid4().hex[:8]}",
                    severity="low",
                    location_block_id=None,
                    description=f"Student simulator could not run: {e}",
                    evidence="",
                    suggested_fix="Retry QC Layer 2.",
                    category="student_simulator",
                )
            )

    all_issues = prog_issues + llm_issues + sim_issues
    for i, issue in enumerate(all_issues):
        if not issue.id:
            issue.id = f"qc2-{i+1}"

    report = QCReport(
        project_id=project_id,
        layer=2,
        lesson_version_id=lv.id,
        issues_json=[iss.model_dump() for iss in all_issues],
        summary=summary,
        score=score,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report
