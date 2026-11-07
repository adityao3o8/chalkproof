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
    <div className="home-shell">
      <div>
        <p className="home-brand">Chalkproof</p>
        <p className="lede">
          Turn a title and learning objective into a grounded 45-minute lesson —
          researched, generated, and checked by two independent QC layers.
        </p>
      </div>
      <form className="panel home-form" onSubmit={onSubmit}>
        <h2>New lesson</h2>
        <label htmlFor="title">Lesson title</label>
        <input
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. HTTP Requests and Responses"
          autoFocus
        />
        <label htmlFor="objective">Learning objective</label>
        <textarea
          id="objective"
          rows={4}
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          placeholder="e.g. Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
        />
        {error && <p className="error">{error}</p>}
        <div className="row" style={{ marginTop: "1.15rem" }}>
          <button type="submit" disabled={busy}>
            {busy ? "Creating…" : "Create project"}
          </button>
        </div>
      </form>
    </div>
  );
}
