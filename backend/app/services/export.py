"""Export lesson + QC reports as markdown/html/json and ZIP."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any, Optional

from sqlmodel import Session, select

from app.models.models import QCReport, Source
from app.models.schemas import LessonContent, QCIssue
from app.services.generate import latest_lesson_version


def lesson_to_markdown(content: LessonContent) -> str:
    lines = [
        f"# {content.title}",
        "",
        f"**Learning objective:** {content.objective}",
        "",
        f"*Estimated time: {content.total_estimated_minutes} minutes*",
        "",
    ]
    for b in content.blocks:
        lines.append(f"## {b.title}")
        lines.append(f"*({b.type} · {b.estimated_minutes} min)*")
        lines.append("")
        lines.append(b.content)
        lines.append("")
    if content.knowledge_checks:
        lines.append("## Knowledge Check Answer Key")
        lines.append("")
        for i, k in enumerate(content.knowledge_checks, 1):
            lines.append(f"### Q{i}. {k.question}")
            lines.append(f"**Answer:** {k.answer}")
            lines.append(f"**Explanation:** {k.explanation}")
            lines.append("")
    return "\n".join(lines)


def lesson_to_html(content: LessonContent) -> str:
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>{_esc(content.title)}</title>",
        "<style>body{font-family:Georgia,serif;max-width:740px;margin:2rem auto;padding:0 1rem;line-height:1.55}"
        "h1,h2{font-family:system-ui,sans-serif}.meta{color:#555}.block{margin:1.5rem 0}</style>",
        "</head><body>",
        f"<h1>{_esc(content.title)}</h1>",
        f"<p class='meta'><strong>Objective:</strong> {_esc(content.objective)}</p>",
        f"<p class='meta'>Estimated time: {content.total_estimated_minutes} minutes</p>",
    ]
    for b in content.blocks:
        parts.append("<div class='block'>")
        parts.append(f"<h2>{_esc(b.title)}</h2>")
        parts.append(f"<p class='meta'>{_esc(b.type)} · {b.estimated_minutes} min</p>")
        # Preserve simple newlines
        html_body = _esc(b.content).replace("\n", "<br>\n")
        # Autolink youtube
        parts.append(f"<div>{html_body}</div>")
        parts.append("</div>")
    parts.append("</body></html>")
    return "\n".join(parts)


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def qc_report_to_markdown(report: QCReport) -> str:
    lines = [
        f"# QC Layer {report.layer} Report",
        "",
        f"**Score:** {report.score}",
        "",
        f"## Summary",
        report.summary or "(none)",
        "",
        "## Issues",
        "",
    ]
    for raw in report.issues_json or []:
        issue = QCIssue.model_validate(raw)
        lines.append(f"### [{issue.severity.upper()}] {issue.id} — {issue.category}")
        lines.append(f"- **Location:** {issue.location_block_id or 'n/a'}")
        lines.append(f"- **Status:** {issue.status}")
        lines.append(f"- **Description:** {issue.description}")
        if issue.evidence:
            lines.append(f"- **Evidence:** {issue.evidence}")
        if issue.suggested_fix:
            lines.append(f"- **Suggested fix:** {issue.suggested_fix}")
        lines.append("")
    return "\n".join(lines)


def references_json(session: Session, project_id: int) -> list[dict[str, Any]]:
    sources = session.exec(select(Source).where(Source.project_id == project_id)).all()
    return [
        {
            "id": s.id,
            "type": s.type,
            "title": s.title,
            "url": s.url,
            "reliability_tier": s.reliability_tier,
            "relevant_segment": s.relevant_segment,
            "video_verified": s.video_verified,
        }
        for s in sources
    ]


def latest_qc(session: Session, project_id: int, layer: int) -> Optional[QCReport]:
    reports = session.exec(
        select(QCReport).where(QCReport.project_id == project_id, QCReport.layer == layer)
    ).all()
    if not reports:
        return None
    return max(reports, key=lambda r: r.created_at)


def build_export_files(session: Session, project_id: int) -> dict[str, str]:
    lv = latest_lesson_version(session, project_id)
    if not lv:
        raise RuntimeError("No lesson to export")
    content = LessonContent.model_validate(lv.content_json)
    files: dict[str, str] = {
        "lesson.md": lesson_to_markdown(content),
        "lesson.html": lesson_to_html(content),
        "references.json": json.dumps(references_json(session, project_id), indent=2),
    }
    r1 = latest_qc(session, project_id, 1)
    r2 = latest_qc(session, project_id, 2)
    files["qc_layer1_report.md"] = qc_report_to_markdown(r1) if r1 else "# QC Layer 1\n\nNo report.\n"
    files["qc_layer2_report.md"] = qc_report_to_markdown(r2) if r2 else "# QC Layer 2\n\nNo report.\n"
    return files


def build_zip(session: Session, project_id: int) -> bytes:
    files = build_export_files(session, project_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()
