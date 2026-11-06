"""Student simulator: novice LLM sees only lesson text and attempts knowledge checks."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.schemas import LessonContent, QCIssue
from app.services.llm import json_completion


class SimAnswer(BaseModel):
    question: str
    student_answer: str
    correct: bool
    confusion_notes: str = ""


class SimResult(BaseModel):
    objective_restatement: str = ""
    objective_understood: bool = True
    answers: list[SimAnswer] = Field(default_factory=list)
    overall_confusion: str = ""


SYSTEM = """You are a novice student who has ONLY read the lesson text below.
You have no prior knowledge of the topic beyond what the lesson teaches.
Answer each knowledge-check question and restate the learning objective in your own words.
Be honest when confused. Return JSON:
{
  "objective_restatement": "...",
  "objective_understood": true/false,
  "answers": [{"question": "...", "student_answer": "...", "correct": true/false, "confusion_notes": "..."}],
  "overall_confusion": "..."
}
Mark correct=false if you are unsure or the lesson did not prepare you.
"""


async def run_student_simulator(content: LessonContent) -> list[QCIssue]:
    lesson_only = "\n\n".join(
        f"## {b.title}\n{b.content}" for b in content.blocks if b.type != "references"
    )
    questions = "\n".join(f"- {k.question}" for k in content.knowledge_checks)
    # Provide expected answers only to the grader side via a second pass —
    # the student prompt must NOT include answers.
    user = (
        f"LESSON TEXT:\n{lesson_only}\n\n"
        f"Learning objective to restate: {content.objective}\n\n"
        f"Questions to answer:\n{questions or '(none provided)'}"
    )
    result = await json_completion("qc", SYSTEM, user, SimResult)

    issues: list[QCIssue] = []
    if not result.objective_understood:
        issues.append(
            QCIssue(
                id=f"qc2-sim-obj-{uuid.uuid4().hex[:8]}",
                severity="high",
                location_block_id=None,
                description="Simulated novice could not restate the learning objective after reading the lesson",
                evidence=f"Student said: {result.objective_restatement!r}. Confusion: {result.overall_confusion}",
                suggested_fix="Add a clearer statement of the objective in the hook/summary and reinforce it in concept blocks.",
                category="student_simulator",
            )
        )

    # Compare against expected answers roughly via confusion flags
    expected = {k.question.strip(): k for k in content.knowledge_checks}
    for ans in result.answers:
        if ans.correct:
            continue
        loc = None
        for b in content.blocks:
            if b.type == "knowledge_check":
                loc = b.id
                break
        exp = expected.get(ans.question.strip())
        hint = exp.explanation if exp else "Clarify the concept tested by this question."
        issues.append(
            QCIssue(
                id=f"qc2-sim-q-{uuid.uuid4().hex[:8]}",
                severity="high",
                location_block_id=loc,
                description=f"Simulated student failed knowledge check: {ans.question}",
                evidence=f"Answered: {ans.student_answer!r}. Notes: {ans.confusion_notes}",
                suggested_fix=f"Strengthen teaching for this topic. Hint from answer key: {hint}",
                category="student_simulator",
            )
        )
    return issues
