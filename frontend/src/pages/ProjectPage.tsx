import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
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
  const [lessonTick, setLessonTick] = useState(0);

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
    return <p>{error || "Loading…"}</p>;
  }

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>{project.title}</h1>
          <p><strong>Objective:</strong> {project.objective}</p>
          <p>Status: <span className={`status ${project.status}`}>{project.status}</span></p>
        </div>
        <div className="row">
          <Link className="btn secondary" to={`/projects/${projectId}/preview`}>Preview</Link>
          <a className="btn" href={api.exportUrl(projectId, "zip")}>Export ZIP</a>
        </div>
      </div>

      <div className="tabs">
        {(["pipeline", "editor", "sources", "qc", "versions"] as const).map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {tab === "pipeline" && (
        <PipelinePanel
          projectId={projectId}
          onDone={() => {
            refresh();
            setLessonTick((x) => x + 1);
          }}
        />
      )}
      {tab === "editor" && (
        <LessonEditor projectId={projectId} refreshKey={lessonTick} />
      )}
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
