"""Pipeline step runner with persisted status and per-step retry."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Awaitable, Any

from sqlmodel import Session, select

from app.models.models import Project, StepStatus
from app.services import research, generate, sandbox, qc1, qc2

logger = logging.getLogger(__name__)

PIPELINE_STEPS = ["research", "generate", "executable", "qc1", "qc2"]


def ensure_steps(session: Session, project_id: int) -> list[StepStatus]:
    existing = {
        s.step: s
        for s in session.exec(select(StepStatus).where(StepStatus.project_id == project_id)).all()
    }
    out = []
    for step in PIPELINE_STEPS:
        if step not in existing:
            row = StepStatus(project_id=project_id, step=step, status="pending")
            session.add(row)
            out.append(row)
        else:
            out.append(existing[step])
    session.commit()
    return out


def get_steps(session: Session, project_id: int) -> list[StepStatus]:
    ensure_steps(session, project_id)
    rows = session.exec(select(StepStatus).where(StepStatus.project_id == project_id)).all()
    order = {s: i for i, s in enumerate(PIPELINE_STEPS)}
    return sorted(rows, key=lambda r: order.get(r.step, 99))


def _set_step(session: Session, project_id: int, step: str, status: str, error: str | None = None) -> None:
    rows = session.exec(
        select(StepStatus).where(StepStatus.project_id == project_id, StepStatus.step == step)
    ).all()
    row = rows[0] if rows else None
    if not row:
        row = StepStatus(project_id=project_id, step=step)
        session.add(row)
    row.status = status
    row.error = error
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()


async def run_step(session: Session, project_id: int, step: str) -> dict[str, Any]:
    if step not in PIPELINE_STEPS:
        raise ValueError(f"Unknown step: {step}")

    project = session.get(Project, project_id)
    if not project:
        raise RuntimeError("Project not found")

    ensure_steps(session, project_id)
    _set_step(session, project_id, step, "running", None)
    project.status = step
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()

    try:
        result: dict[str, Any]
        if step == "research":
            result = await research.run_research(session, project_id, project.title, project.objective)
            project.research_notes = result.get("summary")
        elif step == "generate":
            content = await generate.run_generate(session, project_id, project.title, project.objective)
            result = {"total_estimated_minutes": content.total_estimated_minutes, "blocks": len(content.blocks)}
        elif step == "executable":
            result = await sandbox.run_executable_examples(
                session, project_id, project.title, project.objective
            )
        elif step == "qc1":
            report = await qc1.run_qc1(session, project_id)
            result = {"report_id": report.id, "score": report.score, "issues": len(report.issues_json or [])}
        elif step == "qc2":
            report = await qc2.run_qc2(session, project_id)
            result = {"report_id": report.id, "score": report.score, "issues": len(report.issues_json or [])}
        else:
            raise ValueError(step)

        _set_step(session, project_id, step, "done", None)
        # Refresh project status
        project = session.get(Project, project_id)
        assert project
        if step == "qc2":
            project.status = "ready"
        project.updated_at = datetime.utcnow()
        session.add(project)
        session.commit()
        return {"step": step, "status": "done", "result": result}

    except Exception as e:
        logger.exception("Step %s failed for project %s", step, project_id)
        _set_step(session, project_id, step, "failed", str(e))
        project = session.get(Project, project_id)
        if project:
            project.status = "failed"
            project.updated_at = datetime.utcnow()
            session.add(project)
            session.commit()
        raise


async def run_all(
    session: Session,
    project_id: int,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Run remaining pending/failed steps in order; skip already done unless force=True."""
    results = []
    skipped = 0
    for step in PIPELINE_STEPS:
        steps = {s.step: s for s in get_steps(session, project_id)}
        if not force and steps[step].status == "done":
            results.append({"step": step, "status": "skipped"})
            skipped += 1
            continue
        try:
            results.append(await run_step(session, project_id, step))
        except Exception as e:
            results.append({"step": step, "status": "failed", "error": str(e)})
            break
    return {
        "results": results,
        "force": force,
        "message": (
            "All steps already done — nothing pending. Use Re-run all to run again."
            if skipped == len(PIPELINE_STEPS)
            else None
        ),
    }
