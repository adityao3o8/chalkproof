"""Export endpoints — ZIP and individual files."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session

from app.db import get_session
from app.models.models import Project
from app.services.export import build_export_files, build_zip

router = APIRouter(prefix="/api/projects/{project_id}/export", tags=["export"])


@router.get("/zip")
def export_zip(project_id: int, session: Session = Depends(get_session)):
    if not session.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    try:
        data = build_zip(session, project_id)
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="chalkproof_{project_id}.zip"'},
    )


@router.get("/{filename}")
def export_file(project_id: int, filename: str, session: Session = Depends(get_session)):
    if not session.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    allowed = {
        "lesson.md",
        "lesson.html",
        "references.json",
        "qc_layer1_report.md",
        "qc_layer2_report.md",
    }
    if filename not in allowed:
        raise HTTPException(400, f"Unknown file. Choose from: {sorted(allowed)}")
    try:
        files = build_export_files(session, project_id)
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e
    media = "text/html" if filename.endswith(".html") else (
        "application/json" if filename.endswith(".json") else "text/markdown"
    )
    return Response(
        content=files[filename],
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
