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
  const [info, setInfo] = useState("");

  const load = useCallback(async () => {
    setSteps(await api.steps(projectId));
  }, [projectId]);

  useEffect(() => {
    load();
    const t = setInterval(load, 2500);
    return () => clearInterval(t);
  }, [load]);

  const allDone = STEPS.every((name) => {
    const s = steps.find((x) => x.step === name);
    return s?.status === "done";
  });

  async function run(step: string) {
    setError("");
    setInfo("");
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

  async function runAll(force = false) {
    setError("");
    setInfo("");
    if (!force && allDone) {
      setInfo("All steps are already done — nothing pending. Use “Re-run all” to run again from research.");
      return;
    }
    setBusy("all");
    try {
      const res = await api.runAll(projectId, force);
      if (res?.message) setInfo(res.message);
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
        <div className="row">
          <button onClick={() => runAll(false)} disabled={!!busy}>
            {busy === "all" ? "Running…" : "Run all pending"}
          </button>
          <button className="secondary" onClick={() => runAll(true)} disabled={!!busy}>
            Re-run all
          </button>
        </div>
      </div>
      <p>Each step is persisted and independently retryable. Failures do not erase earlier work.</p>
      {allDone && !busy && (
        <p style={{ color: "var(--ok)" }}>
          Pipeline complete. “Run all pending” will do nothing until a step fails or you click <strong>Re-run all</strong>.
          Per-step <strong>Run</strong> always re-executes that step alone.
        </p>
      )}
      {info && <p>{info}</p>}
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
