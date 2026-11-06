import { useEffect, useState } from "react";
import { api } from "../api";

export default function VersionsPanel({
  projectId,
  onRestored,
}: {
  projectId: number;
  onRestored: () => void;
}) {
  const [versions, setVersions] = useState<any[]>([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      setVersions(await api.versions(projectId));
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, [projectId]);

  async function restore(id: number) {
    await api.restoreVersion(projectId, id);
    await load();
    onRestored();
  }

  if (error) return <p className="error">{error}</p>;

  return (
    <div className="panel">
      <h2>Version history</h2>
      <p>AI generation, QC applies, and manual saves each create a version. Instructor edits are never overwritten by regeneration.</p>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {versions.map((v) => (
          <li key={v.id} className="row" style={{ padding: "0.4rem 0", borderBottom: "1px solid var(--line)" }}>
            <strong>v{v.version}</strong>
            <span>{v.author}</span>
            <span>{v.note}</span>
            <span>{v.total_estimated_minutes != null ? `${v.total_estimated_minutes} min` : ""}</span>
            <span style={{ color: "var(--muted)" }}>{new Date(v.created_at).toLocaleString()}</span>
            <button className="secondary" onClick={() => restore(v.id)}>Restore</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
