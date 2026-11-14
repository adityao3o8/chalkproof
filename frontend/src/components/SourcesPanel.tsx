import { useEffect, useState } from "react";
import { api } from "../api";
import { getSnapshot, upsertSnapshot } from "../localCache";

export default function SourcesPanel({ projectId }: { projectId: number }) {
  const [sources, setSources] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .sources(projectId)
      .then((s) => {
        setSources(s);
        upsertSnapshot(projectId, { sources: s });
      })
      .catch((e) => {
        const cached = getSnapshot(projectId)?.sources;
        if (cached?.length) {
          setSources(cached);
          setError("");
        } else setError(e.message);
      });
  }, [projectId]);

  if (error) return <p className="error">{error}</p>;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Sources</h2>
      </div>
      {!sources.length && <p className="lede">No sources yet — run research.</p>}
      {!!sources.length && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Tier</th>
              <th>Title</th>
              <th>Claims</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.id}>
                <td>{s.type}</td>
                <td>
                  <span className={`status ${s.reliability_tier === "high" ? "done" : ""}`}>
                    {s.reliability_tier}
                  </span>
                </td>
                <td>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.title || s.url}
                  </a>
                </td>
                <td>{s.claim_count}</td>
                <td className="meta">
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
      )}
    </div>
  );
}
