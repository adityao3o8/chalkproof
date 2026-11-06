"""QC report viewing and fix application."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models.models import Project, QCReport
from app.models.schemas import QCIssue, QCIssueUpdate, QCReportOut
from app.services.qc_apply import apply_issue, plant_error, preview_fix_diff

router = APIRouter(prefix="/api/projects/{project_id}/qc", tags=["qc"])


def _to_out(r: QCReport) -> QCReportOut:
    issues = [QCIssue.model_validate(i) for i in (r.issues_json or [])]
    return QCReportOut(
        id=r.id,
        layer=r.layer,
        lesson_version_id=r.lesson_version_id,
        summary=r.summary,
        score=r.score,
        issues=issues,
        created_at=r.created_at,
    )


@router.get("/{layer}", response_model=QCReportOut)
def get_qc_report(project_id: int, layer: int, session: Session = Depends(get_session)):
    if layer not in (1, 2):
        raise HTTPException(400, "layer must be 1 or 2")
    if not session.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    reports = session.exec(
        select(QCReport).where(QCReport.project_id == project_id, QCReport.layer == layer)
    ).all()
    if not reports:
        raise HTTPException(404, f"No QC layer {layer} report yet")
    return _to_out(max(reports, key=lambda r: r.created_at))


@router.get("/{layer}/issues/{issue_id}/diff")
def issue_diff(
    project_id: int,
    layer: int,
    issue_id: str,
    edited_fix: str | None = None,
    session: Session = Depends(get_session),
):
    try:
        return preview_fix_diff(session, project_id, layer, issue_id, edited_fix)
    except RuntimeError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/{layer}/issues/{issue_id}")
def update_issue(
    project_id: int,
    layer: int,
    issue_id: str,
    body: QCIssueUpdate,
    session: Session = Depends(get_session),
):
    try:
        return apply_issue(session, project_id, layer, issue_id, body)
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/plant-error")
def plant_error_demo(project_id: int, session: Session = Depends(get_session)):
    if not session.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    try:
        return plant_error(session, project_id)
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e
