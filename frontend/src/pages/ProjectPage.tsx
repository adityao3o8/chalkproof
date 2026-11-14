import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { exportProjectPdf, exportProjectZip } from "../exportClient";
import {
  getSnapshot,
  restoreProjectToServer,
  upsertSnapshot,
} from "../localCache";
import PipelinePanel from "../components/PipelinePanel";
import LessonEditor from "../components/LessonEditor";
import SourcesPanel from "../components/SourcesPanel";
import QCPanel from "../components/QCPanel";
import VersionsPanel from "../components/VersionsPanel";

export default function ProjectPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const nav = useNavigate();
  const [project, setProject] = useState<any>(null);
  const [tab, setTab] = useState<"pipeline" | "editor" | "sources" | "qc" | "versions">("pipeline");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [exportError, setExportError] = useState("");
  const [exporting, setExporting] = useState<"zip" | "pdf" | "">("");
  const [lessonTick, setLessonTick] = useState(0);
  const [cacheOnly, setCacheOnly] = useState(false);

  async function onExportZip() {
    setExportError("");
    setExporting("zip");
    try {
      await exportProjectZip(projectId);
    } catch (e: any) {
      setExportError(e.message || "Export failed");
    } finally {
      setExporting("");
    }
  }

  async function onExportPdf() {
    setExportError("");
    setExporting("pdf");
    try {
      await exportProjectPdf(projectId);
    } catch (e: any) {
      setExportError(e.message || "PDF export failed");
    } finally {
      setExporting("");
    }
  }

  const refresh = useCallback(async () => {
    setError("");
    try {
      const p = await api.getProject(projectId);
      setProject(p);
      setCacheOnly(false);
      upsertSnapshot(projectId, {
        title: p.title,
        objective: p.objective,
        status: p.status,
      });
      // Keep lesson snapshot fresh when server is up
      try {
        const lesson = await api.lesson(projectId);
        upsertSnapshot(projectId, { lesson });
      } catch {
        /* no lesson yet */
      }
    } catch (e: any) {
      const msg = e.message || "Failed to load project";
      const snap = getSnapshot(projectId);
      if (!snap || !/not found/i.test(msg)) {
        setError(msg);
        setProject(null);
        return;
      }

      // Server DB reset (common on Vercel) — recreate from browser cache
      try {
        const restored = await restoreProjectToServer(
          projectId,
          api.createProject,
          api.saveLesson,
        );
        if (restored) {
          setNotice(
            "Server storage was reset (normal on Vercel). Restored this lesson from your browser and created a fresh server copy.",
          );
          nav(`/projects/${restored.newId}`, { replace: true });
          return;
        }
      } catch {
        /* fall through to cache-only */
      }

      setProject({
        id: snap.id,
        title: snap.title,
        objective: snap.objective,
        status: snap.status,
      });
      setCacheOnly(true);
      setNotice(
        "Showing a browser-cached copy — the Vercel database was cleared. Export still works. Create a new project or re-open from Home to keep editing on the server.",
      );
    }
  }, [projectId, nav]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (!project) {
    return (
      <div>
        <p className="lede">{error || "Loading project…"}</p>
        {error && (
          <p className="notice">
            On Vercel the database resets between cold starts.{" "}
            <Link to="/">Create a new project</Link> (or reopen one from Home → Recent) and
            keep the tab open while you demo — refresh will restore from this browser afterward.
          </p>
        )}
      </div>
    );
  }

  return (
    <div>
      {notice && <p className="notice">{notice}</p>}
      <header className="project-header">
        <div>
          <h1>{project.title}</h1>
          <p className="objective">
            <strong>Objective:</strong> {project.objective}
          </p>
          <span className={`status ${project.status}`}>{project.status}</span>
          {cacheOnly && <span className="status">cached</span>}
        </div>
        <div className="row project-actions">
          <Link className="btn secondary" to={`/projects/${projectId}/preview`}>
            Preview
          </Link>
          <button
            type="button"
            className="btn secondary"
            onClick={onExportPdf}
            disabled={!!exporting}
          >
            {exporting === "pdf" ? "PDF…" : "Export PDF"}
          </button>
          <button type="button" className="btn" onClick={onExportZip} disabled={!!exporting}>
            {exporting === "zip" ? "Exporting…" : "Export ZIP"}
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
