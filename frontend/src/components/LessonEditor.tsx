import { useEffect, useRef, useState } from "react";
import { api } from "../api";

export default function LessonEditor({
  projectId,
  refreshKey,
}: {
  projectId: number;
  refreshKey: number;
}) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const timer = useRef<number | null>(null);

  async function load() {
    try {
      setData(await api.lesson(projectId));
      setError("");
    } catch (e: any) {
      setError(e.message);
      setData(null);
    }
  }

  useEffect(() => {
    load();
  }, [projectId, refreshKey]);

  function scheduleAutosave(next: any) {
    setData(next);
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => save(next.content, "autosave"), 1500);
  }

  async function save(content: any, note = "manual save") {
    setSaving(true);
    setMsg("");
    try {
      const res = await api.saveLesson(projectId, content, note);
      setMsg(`Saved as v${res.version}`);
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (error && !data) return <p className="error">{error}</p>;
  if (!data) return <p>Loading lesson…</p>;

  const content = data.content;
  const minutes = data.minutes;
  const within = minutes.within_budget;

  function updateBlock(i: number, patch: any) {
    const blocks = content.blocks.map((b: any, idx: number) =>
      idx === i ? { ...b, ...patch } : b
    );
    const nextContent = { ...content, blocks };
    const total = blocks.reduce((s: number, b: any) => s + Number(b.estimated_minutes || 0), 0);
    scheduleAutosave({
      ...data,
      content: { ...nextContent, total_estimated_minutes: total },
      minutes: {
        ...minutes,
        total,
        within_budget: Math.abs(total - 45) <= 2,
      },
    });
  }

  return (
    <div className="panel">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>Lesson editor</h2>
        <div className="row">
          <span className={`meter ${within ? "ok" : "warn"}`}>
            {minutes.total} / 45 min {within ? "✓" : "(off target — adjust blocks)"}
          </span>
          <button onClick={() => save(content)} disabled={saving}>
            {saving ? "Saving…" : "Save now"}
          </button>
        </div>
      </div>
      {msg && <p>{msg}</p>}
      {content.blocks.map((b: any, i: number) => (
        <div className="block-editor" key={b.id}>
          <div className="row">
            <strong>{b.type}</strong>
            <input
              style={{ maxWidth: 320 }}
              value={b.title}
              onChange={(e) => updateBlock(i, { title: e.target.value })}
            />
            <label style={{ margin: 0 }}>
              min
              <input
                style={{ width: 70, marginLeft: 6 }}
                type="number"
                step="0.5"
                value={b.estimated_minutes}
                onChange={(e) => updateBlock(i, { estimated_minutes: Number(e.target.value) })}
              />
            </label>
          </div>
          <textarea
            rows={6}
            value={b.content}
            onChange={(e) => updateBlock(i, { content: e.target.value })}
          />
        </div>
      ))}
    </div>
  );
}
