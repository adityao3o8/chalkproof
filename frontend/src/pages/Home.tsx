import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Home() {
  const nav = useNavigate();
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!title.trim() || !objective.trim()) {
      setError("Title and learning objective are required (cannot be empty or whitespace).");
      return;
    }
    setBusy(true);
    try {
      const p = await api.createProject(title, objective);
      nav(`/projects/${p.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create project");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Create a lesson</h1>
      <p>Enter a title and learning objective. Chalkproof will research, generate a 45-minute lesson, and run two independent QC audits.</p>
      <form className="panel" onSubmit={onSubmit}>
        <label htmlFor="title">Lesson title</label>
        <input id="title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. HTTP Requests and Responses" />
        <label htmlFor="objective">Learning objective</label>
        <textarea
          id="objective"
          rows={3}
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          placeholder="e.g. Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
        />
        {error && <p className="error">{error}</p>}
        <div className="row" style={{ marginTop: "1rem" }}>
          <button type="submit" disabled={busy}>{busy ? "Creating…" : "Create project"}</button>
        </div>
      </form>
    </div>
  );
}
