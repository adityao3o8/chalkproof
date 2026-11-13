import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { exportProjectZip } from "../exportClient";
import PipelinePanel from "../components/PipelinePanel";
import LessonEditor from "../components/LessonEditor";
import SourcesPanel from "../components/SourcesPanel";
import QCPanel from "../components/QCPanel";
import VersionsPanel from "../components/VersionsPanel";

export default function ProjectPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const [project, setProject] = useState<any>(null);
  const [tab, setTab] = useState<"pipeline" | "editor" | "sources" | "qc" | "versions">("pipeline");
  const [error, setError] = useState("");
  const [exportError, setExportError] = useState("");
  const [exporting, setExporting] = useState(false);
  const [lessonTick, setLessonTick] = useState(0);

  async function onExportZip() {
    setExportError("");
    setExporting(true);
    try {
      await exportProjectZip(projectId);
    } catch (e: any) {
      setExportError(e.message || "Export failed");
    } finally {
      setExporting(false);
    }
  }

  const refresh = useCallback(async () => {
    try {
      setProject(await api.getProject(projectId));
    } catch (e: any) {
      setError(e.message);
    }
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (!project) {
    return <p className="lede">{error || "Loading project…"}</p>;
  }

  return (
    <div>
      <header className="project-header">
        <div>
          <h1>{project.title}</h1>
          <p className="objective">
            <strong>Objective:</strong> {project.objective}
          </p>
          <span className={`status ${project.status}`}>{project.status}</span>
        </div>
        <div className="row project-actions">
          <Link className="btn secondary" to={`/projects/${projectId}/preview`}>
            Preview
          </Link>
          <button type="button" className="btn" onClick={onExportZip} disabled={exporting}>
            {exporting ? "Exporting…" : "Export ZIP"}
          </button>
        </div>
      </header>
      {exportError && <p className="error">{exportError}</p>}

      <nav className="tabs" aria-label="Project sections">
        {(["pipeline", "editor", "sources", "qc", "versions"] as const).map((t) => (
          <button
            key={t}
            type="button"
            className={tab === t ? "active" : ""}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </nav>

      {tab === "pipeline" && (
        <PipelinePanel
          projectId={projectId}
          onDone={() => {
            refresh();
            setLessonTick((x) => x + 1);
          }}
        />
      )}
      {tab === "editor" && <LessonEditor projectId={projectId} refreshKey={lessonTick} />}
      {tab === "sources" && <SourcesPanel projectId={projectId} />}
      {tab === "qc" && (
        <QCPanel
          projectId={projectId}
          onApplied={() => {
            setLessonTick((x) => x + 1);
            refresh();
          }}
        />
      )}
      {tab === "versions" && (
        <VersionsPanel
          projectId={projectId}
          onRestored={() => {
            setLessonTick((x) => x + 1);
            setTab("editor");
          }}
        />
      )}
    </div>
  );
}
