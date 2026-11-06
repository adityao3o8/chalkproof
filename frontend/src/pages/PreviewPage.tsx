import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";

export default function PreviewPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.lesson(projectId).then(setData).catch((e) => setError(e.message));
  }, [projectId]);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading preview…</p>;
  const c = data.content;

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <Link to={`/projects/${projectId}`}>← Back to project</Link>
        <div className="row">
          <a className="btn secondary" href={api.exportUrl(projectId, "lesson.md")}>lesson.md</a>
          <a className="btn secondary" href={api.exportUrl(projectId, "lesson.html")}>lesson.html</a>
          <a className="btn" href={api.exportUrl(projectId, "zip")}>ZIP</a>
        </div>
      </div>
      <article className="panel">
        <h1>{c.title}</h1>
        <p><strong>Learning objective:</strong> {c.objective}</p>
        <p className="meta">Estimated time: {c.total_estimated_minutes} minutes</p>
        {c.blocks.map((b: any) => (
          <section className="preview-block" key={b.id}>
            <h2>{b.title}</h2>
            <p className="meta">{b.type} · {b.estimated_minutes} min</p>
            <div style={{ whiteSpace: "pre-wrap" }}>{b.content}</div>
          </section>
        ))}
      </article>
    </div>
  );
}
