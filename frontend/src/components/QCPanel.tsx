import { useEffect, useState } from "react";
import { api } from "../api";
import { getSnapshot, upsertSnapshot } from "../localCache";

export default function QCPanel({
  projectId,
  onApplied,
}: {
  projectId: number;
  onApplied: () => void;
}) {
  const [layer, setLayer] = useState<1 | 2>(1);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState("");
  const [diff, setDiff] = useState<any>(null);
  const [editText, setEditText] = useState("");
  const [activeIssue, setActiveIssue] = useState<string | null>(null);

  async function load(l: 1 | 2 = layer) {
    setError("");
    try {
      const report = await api.qc(projectId, l);
      setReport(report);
      upsertSnapshot(projectId, l === 1 ? { qc1: report } : { qc2: report });
    } catch (e: any) {
      const snap = getSnapshot(projectId);
      const cached = l === 1 ? snap?.qc1 : snap?.qc2;
      if (cached) {
        setReport(cached);
        return;
      }
      setReport(null);
      setError(e.message);
    }
  }

  useEffect(() => {
    load(layer);
  }, [projectId, layer]);

  async function showDiff(issueId: string) {
    setActiveIssue(issueId);
    const d = await api.qcDiff(projectId, layer, issueId);
    setDiff(d);
    setEditText(d.suggested_fix || "");
  }

  async function act(issueId: string, action: "accept" | "reject" | "edit") {
    await api.qcAction(projectId, layer, issueId, action, action === "edit" ? editText : undefined);
    setDiff(null);
    setActiveIssue(null);
    await load();
    onApplied();
  }

  async function plant() {
    const res = await api.plantError(projectId);
    alert(res.message);
    onApplied();
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="tabs" style={{ marginBottom: 0, borderBottom: "none" }}>
          <button
            type="button"
            className={layer === 1 ? "active" : ""}
            onClick={() => setLayer(1)}
          >
            Layer 1 — Factual
          </button>
          <button
            type="button"
            className={layer === 2 ? "active" : ""}
            onClick={() => setLayer(2)}
          >
            Layer 2 — Instructional
          </button>
        </div>
        <button type="button" className="secondary" onClick={plant}>
          Plant error demo
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {report && (
        <>
          <p>
            <strong>Score:</strong> {report.score} — {report.summary}
          </p>
          {(report.issues || []).map((iss: any) => (
            <div className="issue" key={iss.id}>
              <div className="row">
                <span className={`sev-${iss.severity}`}>{iss.severity}</span>
                <strong>{iss.id}</strong>
                <span className="meta">{iss.category}</span>
                <span className={`status ${iss.status}`}>{iss.status}</span>
              </div>
              <p>{iss.description}</p>
              {iss.evidence && (
                <p className="meta">
                  Evidence: {iss.evidence}
                </p>
              )}
              {iss.status === "open" && (
                <div className="row" style={{ marginTop: "0.5rem" }}>
                  <button type="button" className="secondary" onClick={() => showDiff(iss.id)}>
                    Review / diff
                  </button>
                  <button type="button" onClick={() => act(iss.id, "accept")}>
                    Accept
                  </button>
                  <button type="button" className="danger" onClick={() => act(iss.id, "reject")}>
                    Reject
                  </button>
                </div>
              )}
              {activeIssue === iss.id && diff && (
                <div>
                  <div className="diff">
                    <div>
                      <strong>Before</strong>
                      <pre>{diff.before}</pre>
                    </div>
                    <div>
                      <strong>Suggested / edit</strong>
                      <textarea
                        rows={8}
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="row" style={{ marginTop: "0.5rem" }}>
                    <button type="button" onClick={() => act(iss.id, "accept")}>
                      Apply suggested
                    </button>
                    <button type="button" onClick={() => act(iss.id, "edit")}>
                      Edit then apply
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => {
                        setDiff(null);
                        setActiveIssue(null);
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
