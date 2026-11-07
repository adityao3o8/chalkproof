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
      <div className="panel-header">
        <h2>Version history</h2>
      </div>
      <p className="lede">
        AI generation, QC applies, and manual saves each create a version. Instructor edits are never
        overwritten by regeneration.
      </p>
      <div>
        {versions.map((v) => (
          <div key={v.id} className="version-row">
            <strong>v{v.version}</strong>
            <span>{v.author}</span>
            <span>{v.note}</span>
            <span className="muted">
              {v.total_estimated_minutes != null ? `${v.total_estimated_minutes} min` : ""}
            </span>
            <span className="muted">{new Date(v.created_at).toLocaleString()}</span>
            <button type="button" className="secondary" onClick={() => restore(v.id)}>
              Restore
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
