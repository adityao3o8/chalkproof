"""Apply / reject / edit QC suggested fixes onto the lesson."""

from __future__ import annotations

import copy
from typing import Any, Optional

from sqlmodel import Session, select

from app.models.models import QCReport
from app.models.schemas import LessonClaim, LessonContent, QCIssueUpdate
from app.services.generate import latest_lesson_version, save_instructor_version


def _latest_report(session: Session, project_id: int, layer: int) -> QCReport:
    reports = session.exec(
        select(QCReport).where(QCReport.project_id == project_id, QCReport.layer == layer)
    ).all()
    if not reports:
        raise RuntimeError(f"No QC layer {layer} report")
    return max(reports, key=lambda r: r.created_at)


def preview_fix_diff(
    session: Session,
    project_id: int,
    layer: int,
    issue_id: str,
    edited_fix: Optional[str] = None,
) -> dict[str, Any]:
    report = _latest_report(session, project_id, layer)
    issue = next((i for i in report.issues_json if i.get("id") == issue_id), None)
    if not issue:
        raise RuntimeError("Issue not found")
    lv = latest_lesson_version(session, project_id)
    if not lv:
        raise RuntimeError("No lesson")
    content = LessonContent.model_validate(lv.content_json)
    block_id = issue.get("location_block_id")
    before = ""
    for b in content.blocks:
        if b.id == block_id:
            before = b.content
            break
    after_text = edited_fix if edited_fix is not None else (issue.get("suggested_fix") or "")
    return {
        "issue_id": issue_id,
        "block_id": block_id,
        "before": before,
        "after": after_text if after_text else before,
        "suggested_fix": issue.get("suggested_fix") or "",
    }


def apply_issue(
    session: Session,
    project_id: int,
    layer: int,
    issue_id: str,
    update: QCIssueUpdate,
) -> dict[str, Any]:
    report = _latest_report(session, project_id, layer)
    issues = list(report.issues_json or [])
    idx = next((i for i, x in enumerate(issues) if x.get("id") == issue_id), None)
    if idx is None:
        raise RuntimeError("Issue not found")

    issue = dict(issues[idx])
    lv = latest_lesson_version(session, project_id)
    if not lv:
        raise RuntimeError("No lesson")
    content = LessonContent.model_validate(copy.deepcopy(lv.content_json))

    if update.action == "reject":
        issue["status"] = "rejected"
        issues[idx] = issue
        report.issues_json = issues
        session.add(report)
        session.commit()
        return {"status": "rejected", "issue": issue}

    fix_text = update.edited_fix if update.action == "edit" else issue.get("suggested_fix")
    if update.action == "edit" and not update.edited_fix:
        raise RuntimeError("edited_fix required for edit action")

    block_id = issue.get("location_block_id")
    applied = False
    if block_id and fix_text:
        for b in content.blocks:
            if b.id == block_id:
                # If suggested_fix looks like a full block replacement, replace;
                # otherwise append a correction note.
                if len(fix_text) > 80 or "\n" in fix_text:
                    b.content = fix_text
                else:
                    b.content = b.content.rstrip() + f"\n\n*[QC fix applied]* {fix_text}"
                applied = True
                break
    elif fix_text and not block_id:
        # Global note on summary block or append concept
        for b in content.blocks:
            if b.type == "summary":
                b.content = b.content.rstrip() + f"\n\n*[QC note]* {fix_text}"
                applied = True
                break

    issue["status"] = "edited" if update.action == "edit" else "accepted"
    if update.action == "edit" and update.edited_fix:
        issue["suggested_fix"] = update.edited_fix
    issues[idx] = issue
    report.issues_json = issues
    session.add(report)
    session.commit()

    if applied:
        save_instructor_version(
            session,
            project_id,
            content,
            note=f"QC{layer} {update.action} {issue_id}",
        )

    return {"status": issue["status"], "applied": applied, "issue": issue}


def plant_error(session: Session, project_id: int) -> dict[str, Any]:
    """Inject a known false claim for demo purposes, then caller re-runs QC1."""
    lv = latest_lesson_version(session, project_id)
    if not lv:
        raise RuntimeError("No lesson — generate first")
    content = LessonContent.model_validate(copy.deepcopy(lv.content_json))
    false_claim = (
        "Important note: HTTP status code 401 is a 5xx server error indicating "
        "the server failed to process the request."
    )
    planted_block_id = None
    for b in content.blocks:
        if b.type in ("concept", "worked_example"):
            b.content = b.content.rstrip() + "\n\n" + false_claim
            planted_block_id = b.id
            break
    if not planted_block_id and content.blocks:
        content.blocks[0].content += "\n\n" + false_claim
        planted_block_id = content.blocks[0].id

    content.claims.append(
        LessonClaim(
            claim_text="401 is a 5xx server error",
            source_id=0,
            supporting_quote="this quote does not exist in any source",
            block_id=planted_block_id or "b1",
        )
    )
    save_instructor_version(session, project_id, content, note="planted error demo")
    return {
        "planted": True,
        "false_claim": false_claim,
        "block_id": planted_block_id,
        "message": "False claim planted. Re-run QC Layer 1 to see it caught.",
    }
