"""Lesson editor, versions, preview data."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models.models import LessonVersion, Project
from app.models.schemas import LessonContent, LessonSave, VersionOut
from app.services.generate import latest_lesson_version, save_instructor_version
from app.utils.time_budget import TARGET_MINUTES, TOLERANCE, is_within_budget

router = APIRouter(prefix="/api/projects/{project_id}/lesson", tags=["lesson"])


@router.get("")
def get_lesson(project_id: int, session: Session = Depends(get_session)):
    if not session.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    lv = latest_lesson_version(session, project_id)
    if not lv:
        raise HTTPException(404, "No lesson yet — run generate")
    content = LessonContent.model_validate(lv.content_json)
    total = content.recomputed_minutes()
    return {
        "version_id": lv.id,
        "version": lv.version,
        "author": lv.author,
        "content": content,
        "minutes": {
            "total": total,
            "target": TARGET_MINUTES,
            "tolerance": TOLERANCE,
            "within_budget": is_within_budget(total),
        },
    }


@router.put("")
def save_lesson(project_id: int, body: LessonSave, session: Session = Depends(get_session)):
    if not session.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    content = body.content
    content.total_estimated_minutes = content.recomputed_minutes()
    lv = save_instructor_version(session, project_id, content, note=body.note or "manual save")
    return {"version": lv.version, "version_id": lv.id, "total": content.total_estimated_minutes}


@router.get("/versions", response_model=list[VersionOut])
def list_versions(project_id: int, session: Session = Depends(get_session)):
    if not session.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    versions = session.exec(
        select(LessonVersion).where(LessonVersion.project_id == project_id)
    ).all()
    out = []
    for v in sorted(versions, key=lambda x: x.version, reverse=True):
        mins = None
        try:
            mins = LessonContent.model_validate(v.content_json).recomputed_minutes()
        except Exception:
            pass
        out.append(
            VersionOut(
                id=v.id,
                version=v.version,
                author=v.author,
                note=v.note,
                created_at=v.created_at,
                total_estimated_minutes=mins,
            )
        )
    return out


@router.get("/versions/{version_id}")
def get_version(project_id: int, version_id: int, session: Session = Depends(get_session)):
    v = session.get(LessonVersion, version_id)
    if not v or v.project_id != project_id:
        raise HTTPException(404, "Version not found")
    return {"version": v.version, "author": v.author, "note": v.note, "content": v.content_json}


@router.post("/versions/{version_id}/restore")
def restore_version(project_id: int, version_id: int, session: Session = Depends(get_session)):
    v = session.get(LessonVersion, version_id)
    if not v or v.project_id != project_id:
        raise HTTPException(404, "Version not found")
    content = LessonContent.model_validate(v.content_json)
    new_v = save_instructor_version(
        session, project_id, content, note=f"restored from v{v.version}"
    )
    return {"version": new_v.version, "restored_from": v.version}
