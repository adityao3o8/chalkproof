import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

const STEPS = ["research", "generate", "executable", "qc1", "qc2"];

export default function PipelinePanel({
  projectId,
  onDone,
}: {
  projectId: number;
  onDone: () => void;
}) {
  const [steps, setSteps] = useState<any[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setSteps(await api.steps(projectId));
  }, [projectId]);

  useEffect(() => {
    load();
    const t = setInterval(load, 2500);
    return () => clearInterval(t);
  }, [load]);

  async function run(step: string) {
    setError("");
    setBusy(step);
    try {
      await api.runStep(projectId, step);
      await load();
      onDone();
    } catch (e: any) {
      setError(e.message);
      await load();
    } finally {
      setBusy(null);
    }
  }

  async function runAll() {
    setError("");
    setBusy("all");
    try {
      await api.runAll(projectId);
      await load();
      onDone();
    } catch (e: any) {
      setError(e.message);
      await load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="panel">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>Pipeline</h2>
        <button onClick={runAll} disabled={!!busy}>
          {busy === "all" ? "Running…" : "Run all pending"}
        </button>
      </div>
      <p>Each step is persisted and independently retryable. Failures do not erase earlier work.</p>
      {error && <p className="error">{error}</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {STEPS.map((name) => {
          const s = steps.find((x) => x.step === name) || { status: "pending" };
          return (
            <li key={name} className="row" style={{ padding: "0.5rem 0", borderBottom: "1px solid var(--line)" }}>
              <strong style={{ width: 120 }}>{name}</strong>
              <span className={`status ${s.status}`}>{s.status}</span>
              {s.error && <span className="error" style={{ flex: 1 }}>{s.error}</span>}
              <button
                className="secondary"
                disabled={!!busy}
                onClick={() => run(name)}
              >
                {s.status === "failed" ? "Retry" : busy === name ? "Running…" : "Run"}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
