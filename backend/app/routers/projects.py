"""Project CRUD and pipeline status."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models.models import Claim, Project, Source
from app.models.schemas import ProjectCreate, ProjectOut, SourceOut, StepStatusOut
from app.services.pipeline import ensure_steps, get_steps

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate, session: Session = Depends(get_session)):
    try:
        data = ProjectCreate.model_validate(body.model_dump())
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    project = Project(title=data.title, objective=data.objective, status="created")
    session.add(project)
    session.commit()
    session.refresh(project)
    ensure_steps(session, project.id)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(session: Session = Depends(get_session)):
    return session.exec(select(Project).order_by(Project.created_at.desc())).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/{project_id}/steps", response_model=list[StepStatusOut])
def project_steps(project_id: int, session: Session = Depends(get_session)):
    if not session.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    return get_steps(session, project_id)


@router.get("/{project_id}/sources", response_model=list[SourceOut])
def project_sources(project_id: int, session: Session = Depends(get_session)):
    if not session.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    sources = session.exec(select(Source).where(Source.project_id == project_id)).all()
    # Count claims citing each source across all versions — prefer latest via any claim
    claims = session.exec(select(Claim)).all()
    counts: dict[int, int] = {}
    for c in claims:
        if c.source_id:
            counts[c.source_id] = counts.get(c.source_id, 0) + 1
    return [
        SourceOut(
            id=s.id,
            type=s.type,
            url=s.url,
            title=s.title,
            reliability_tier=s.reliability_tier,
            relevant_segment=s.relevant_segment,
            video_verified=s.video_verified,
            claim_count=counts.get(s.id or 0, 0),
        )
        for s in sources
    ]
