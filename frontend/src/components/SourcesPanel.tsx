import { useEffect, useState } from "react";
import { api } from "../api";

export default function SourcesPanel({ projectId }: { projectId: number }) {
  const [sources, setSources] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.sources(projectId).then(setSources).catch((e) => setError(e.message));
  }, [projectId]);

  if (error) return <p className="error">{error}</p>;

  return (
    <div className="panel">
      <h2>Sources</h2>
      {!sources.length && <p>No sources yet — run research.</p>}
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th align="left">Type</th>
            <th align="left">Tier</th>
            <th align="left">Title</th>
            <th align="left">Claims</th>
            <th align="left">Notes</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((s) => (
            <tr key={s.id} style={{ borderTop: "1px solid var(--line)" }}>
              <td>{s.type}</td>
              <td>{s.reliability_tier}</td>
              <td>
                <a href={s.url} target="_blank" rel="noreferrer">{s.title || s.url}</a>
              </td>
              <td>{s.claim_count}</td>
              <td>
                {s.type === "video" && (
                  <>
                    {s.relevant_segment || "—"}{" "}
                    {!s.video_verified && <em>(unverified — no transcript)</em>}
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
