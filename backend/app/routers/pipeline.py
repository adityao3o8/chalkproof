"""Per-step pipeline endpoints — each independently retryable."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.models.models import Project
from app.services.pipeline import PIPELINE_STEPS, run_all, run_step

router = APIRouter(prefix="/api/projects/{project_id}/pipeline", tags=["pipeline"])


def _require_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.post("/{step}")
async def run_pipeline_step(project_id: int, step: str, session: Session = Depends(get_session)):
    _require_project(session, project_id)
    if step not in PIPELINE_STEPS and step != "all":
        raise HTTPException(400, f"Unknown step. Choose from: {PIPELINE_STEPS} or 'all'")
    try:
        if step == "all":
            return await run_all(session, project_id)
        return await run_step(session, project_id, step)
    except Exception as e:
        raise HTTPException(500, f"Step '{step}' failed: {e}") from e


@router.post("/run")
async def run_full_pipeline(project_id: int, session: Session = Depends(get_session)):
    _require_project(session, project_id)
    try:
        return await run_all(session, project_id)
    except Exception as e:
        raise HTTPException(500, str(e)) from e
