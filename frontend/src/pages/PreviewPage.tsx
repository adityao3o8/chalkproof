import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { downloadLessonFile, downloadLessonPdf, exportProjectZip } from "../exportClient";

export default function PreviewPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api.lesson(projectId).then(setData).catch((e) => setError(e.message));
  }, [projectId]);

  async function onZip() {
    setBusy("zip");
    setError("");
    try {
      await exportProjectZip(projectId, data?.content);
    } catch (e: any) {
      setError(e.message || "Export failed");
    } finally {
      setBusy("");
    }
  }

  async function onPdf() {
    setBusy("pdf");
    setError("");
    try {
      await downloadLessonPdf(data.content, `chalkproof_${projectId}.pdf`);
    } catch (e: any) {
      setError(e.message || "PDF export failed");
    } finally {
      setBusy("");
    }
  }

  if (error && !data) return <p className="error">{error}</p>;
  if (!data) return <p className="lede">Loading preview…</p>;
  const c = data.content;

  return (
    <div>
      <div className="preview-toolbar">
        <Link to={`/projects/${projectId}`}>← Back to project</Link>
        <div className="row">
          <button
            type="button"
            className="btn secondary"
            onClick={() => downloadLessonFile(c, "md")}
          >
            lesson.md
          </button>
          <button
            type="button"
            className="btn secondary"
            onClick={() => downloadLessonFile(c, "html")}
          >
            lesson.html
          </button>
          <button type="button" className="btn secondary" onClick={onPdf} disabled={!!busy}>
            {busy === "pdf" ? "PDF…" : "PDF"}
          </button>
          <button type="button" className="btn" onClick={onZip} disabled={!!busy}>
            {busy === "zip" ? "Exporting…" : "ZIP"}
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <article className="preview-doc">
        <h1>{c.title}</h1>
        <p>
          <strong>Learning objective:</strong> {c.objective}
        </p>
        <p className="meta">Estimated time: {c.total_estimated_minutes} minutes</p>
        {c.blocks.map((b: any) => (
          <section className="preview-block" key={b.id}>
            <h2>{b.title}</h2>
            <p className="meta">
              {b.type} · {b.estimated_minutes} min
            </p>
            <div className="preview-body">{b.content}</div>
          </section>
        ))}
      </article>
    </div>
  );
}
