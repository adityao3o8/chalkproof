/** Browser snapshots — survive Vercel’s ephemeral /tmp SQLite on refresh. */

export type ProjectSnapshot = {
  id: number;
  title: string;
  objective: string;
  status: string;
  lesson?: {
    version_id?: number;
    version?: number;
    author?: string;
    content: any;
    minutes?: any;
  } | null;
  sources?: any[];
  steps?: any[];
  qc1?: any | null;
  qc2?: any | null;
  updatedAt: string;
};

const KEY = "chalkproof.snapshots.v1";

function readAll(): Record<string, ProjectSnapshot> {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeAll(map: Record<string, ProjectSnapshot>) {
  try {
    localStorage.setItem(KEY, JSON.stringify(map));
  } catch {
    /* quota / private mode */
  }
}

export function listSnapshots(): ProjectSnapshot[] {
  return Object.values(readAll()).sort((a, b) =>
    (b.updatedAt || "").localeCompare(a.updatedAt || ""),
  );
}

export function getSnapshot(id: number): ProjectSnapshot | null {
  return readAll()[String(id)] || null;
}

export function upsertSnapshot(
  id: number,
  patch: Partial<ProjectSnapshot> & { title?: string; objective?: string },
): ProjectSnapshot {
  const map = readAll();
  const prev = map[String(id)];
  const next: ProjectSnapshot = {
    id,
    title: patch.title ?? prev?.title ?? "Untitled",
    objective: patch.objective ?? prev?.objective ?? "",
    status: patch.status ?? prev?.status ?? "created",
    lesson: patch.lesson !== undefined ? patch.lesson : prev?.lesson,
    sources: patch.sources !== undefined ? patch.sources : prev?.sources,
    steps: patch.steps !== undefined ? patch.steps : prev?.steps,
    qc1: patch.qc1 !== undefined ? patch.qc1 : prev?.qc1,
    qc2: patch.qc2 !== undefined ? patch.qc2 : prev?.qc2,
    updatedAt: new Date().toISOString(),
  };
  map[String(id)] = next;
  writeAll(map);
  return next;
}

export function migrateSnapshot(fromId: number, toId: number): ProjectSnapshot | null {
  const map = readAll();
  const snap = map[String(fromId)];
  if (!snap) return null;
  const moved = { ...snap, id: toId, updatedAt: new Date().toISOString() };
  map[String(toId)] = moved;
  delete map[String(fromId)];
  writeAll(map);
  return moved;
}

/** If the server lost the project, recreate it from the browser snapshot. */
export async function restoreProjectToServer(
  id: number,
  createProject: (title: string, objective: string) => Promise<{ id: number; title?: string; objective?: string; status?: string }>,
  saveLesson: (id: number, content: any, note?: string) => Promise<any>,
): Promise<{ project: any; newId: number } | null> {
  const snap = getSnapshot(id);
  if (!snap) return null;
  const created = await createProject(snap.title, snap.objective);
  if (snap.lesson?.content) {
    try {
      await saveLesson(created.id, snap.lesson.content, "restored from browser after storage reset");
    } catch {
      /* lesson optional */
    }
  }
  migrateSnapshot(id, created.id);
  upsertSnapshot(created.id, {
    title: snap.title,
    objective: snap.objective,
    status: created.status || snap.status,
    lesson: snap.lesson,
    sources: snap.sources,
    steps: snap.steps,
    qc1: snap.qc1,
    qc2: snap.qc2,
  });
  return {
    project: {
      id: created.id,
      title: snap.title,
      objective: snap.objective,
      status: created.status || "created",
    },
    newId: created.id,
  };
}
