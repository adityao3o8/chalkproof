const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res as unknown as T;
}

export const api = {
  health: () => req<{ ok: boolean; generator_model: string; qc_model: string }>("/api/health"),
  createProject: (title: string, objective: string) =>
    req<{ id: number }>("/api/projects", {
      method: "POST",
      body: JSON.stringify({ title, objective }),
    }),
  getProject: (id: number) => req<any>(`/api/projects/${id}`),
  steps: (id: number) => req<any[]>(`/api/projects/${id}/steps`),
  sources: (id: number) => req<any[]>(`/api/projects/${id}/sources`),
  runStep: (id: number, step: string) =>
    req<any>(`/api/projects/${id}/pipeline/${step}`, { method: "POST" }),
  runAll: (id: number, force = false) =>
    req<any>(`/api/projects/${id}/pipeline/run?force=${force ? "true" : "false"}`, {
      method: "POST",
    }),
  lesson: (id: number) => req<any>(`/api/projects/${id}/lesson`),
  saveLesson: (id: number, content: any, note?: string) =>
    req<any>(`/api/projects/${id}/lesson`, {
      method: "PUT",
      body: JSON.stringify({ content, note }),
    }),
  versions: (id: number) => req<any[]>(`/api/projects/${id}/lesson/versions`),
  restoreVersion: (id: number, versionId: number) =>
    req<any>(`/api/projects/${id}/lesson/versions/${versionId}/restore`, { method: "POST" }),
  qc: (id: number, layer: 1 | 2) => req<any>(`/api/projects/${id}/qc/${layer}`),
  qcDiff: (id: number, layer: 1 | 2, issueId: string) =>
    req<any>(`/api/projects/${id}/qc/${layer}/issues/${encodeURIComponent(issueId)}/diff`),
  qcAction: (id: number, layer: 1 | 2, issueId: string, action: string, edited_fix?: string) =>
    req<any>(`/api/projects/${id}/qc/${layer}/issues/${encodeURIComponent(issueId)}`, {
      method: "POST",
      body: JSON.stringify({ action, edited_fix }),
    }),
  plantError: (id: number) =>
    req<any>(`/api/projects/${id}/qc/plant-error`, { method: "POST" }),
  exportUrl: (id: number, file: string) => `${BASE}/api/projects/${id}/export/${file}`,
};
