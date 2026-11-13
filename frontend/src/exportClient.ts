/** Client-side lesson export — avoids Vercel /tmp SQLite cold-start 404s. */

import { api } from "./api";

type LessonContent = {
  title: string;
  objective: string;
  total_estimated_minutes: number;
  blocks: { id: string; title: string; type: string; estimated_minutes: number; content: string }[];
  knowledge_checks?: { question: string; answer: string; explanation: string }[];
};

type QCReport = {
  layer: number;
  score?: number | null;
  summary?: string | null;
  issues?: {
    id: string;
    category: string;
    severity: string;
    status: string;
    description: string;
    location_block_id?: string | null;
    evidence?: string | null;
    suggested_fix?: string | null;
  }[];
};

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function lessonToMarkdown(c: LessonContent): string {
  const lines = [
    `# ${c.title}`,
    "",
    `**Learning objective:** ${c.objective}`,
    "",
    `*Estimated time: ${c.total_estimated_minutes} minutes*`,
    "",
  ];
  for (const b of c.blocks) {
    lines.push(`## ${b.title}`, `*(${b.type} · ${b.estimated_minutes} min)*`, "", b.content, "");
  }
  if (c.knowledge_checks?.length) {
    lines.push("## Knowledge Check Answer Key", "");
    c.knowledge_checks.forEach((k, i) => {
      lines.push(
        `### Q${i + 1}. ${k.question}`,
        `**Answer:** ${k.answer}`,
        `**Explanation:** ${k.explanation}`,
        "",
      );
    });
  }
  return lines.join("\n");
}

export function lessonToHtml(c: LessonContent): string {
  const parts = [
    "<!DOCTYPE html><html><head><meta charset='utf-8'>",
    `<title>${esc(c.title)}</title>`,
    "<style>body{font-family:Georgia,serif;max-width:740px;margin:2rem auto;padding:0 1rem;line-height:1.55}" +
      "h1,h2{font-family:system-ui,sans-serif}.meta{color:#555}.block{margin:1.5rem 0}</style>",
    "</head><body>",
    `<h1>${esc(c.title)}</h1>`,
    `<p class='meta'><strong>Objective:</strong> ${esc(c.objective)}</p>`,
    `<p class='meta'>Estimated time: ${c.total_estimated_minutes} minutes</p>`,
  ];
  for (const b of c.blocks) {
    parts.push(
      "<div class='block'>",
      `<h2>${esc(b.title)}</h2>`,
      `<p class='meta'>${esc(b.type)} · ${b.estimated_minutes} min</p>`,
      `<div>${esc(b.content).replace(/\n/g, "<br>\n")}</div>`,
      "</div>",
    );
  }
  parts.push("</body></html>");
  return parts.join("\n");
}

export function qcToMarkdown(report: QCReport | null, layer: number): string {
  if (!report) return `# QC Layer ${layer}\n\nNo report.\n`;
  const lines = [
    `# QC Layer ${report.layer} Report`,
    "",
    `**Score:** ${report.score ?? ""}`,
    "",
    "## Summary",
    report.summary || "(none)",
    "",
    "## Issues",
    "",
  ];
  for (const issue of report.issues || []) {
    lines.push(
      `### [${issue.severity.toUpperCase()}] ${issue.id} — ${issue.category}`,
      `- **Location:** ${issue.location_block_id || "n/a"}`,
      `- **Status:** ${issue.status}`,
      `- **Description:** ${issue.description}`,
    );
    if (issue.evidence) lines.push(`- **Evidence:** ${issue.evidence}`);
    if (issue.suggested_fix) lines.push(`- **Suggested fix:** ${issue.suggested_fix}`);
    lines.push("");
  }
  return lines.join("\n");
}

/* Minimal ZIP (STORE) — no compression dependency */
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[i] = c;
  }
  return t;
})();

function crc32(data: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < data.length; i++) c = CRC_TABLE[(c ^ data[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function u16(n: number): Uint8Array {
  const b = new Uint8Array(2);
  new DataView(b.buffer).setUint16(0, n, true);
  return b;
}

function u32(n: number): Uint8Array {
  const b = new Uint8Array(4);
  new DataView(b.buffer).setUint32(0, n, true);
  return b;
}

function concat(parts: Uint8Array[]): Uint8Array {
  const len = parts.reduce((a, p) => a + p.length, 0);
  const out = new Uint8Array(len);
  let o = 0;
  for (const p of parts) {
    out.set(p, o);
    o += p.length;
  }
  return out;
}

export function buildZip(files: Record<string, string>): Blob {
  const enc = new TextEncoder();
  const locals: Uint8Array[] = [];
  const centrals: Uint8Array[] = [];
  let offset = 0;

  for (const [name, text] of Object.entries(files)) {
    const nameBytes = enc.encode(name);
    const data = enc.encode(text);
    const crc = crc32(data);
    const local = concat([
      u32(0x04034b50),
      u16(20),
      u16(0),
      u16(0),
      u16(0),
      u16(0),
      u32(crc),
      u32(data.length),
      u32(data.length),
      u16(nameBytes.length),
      u16(0),
      nameBytes,
      data,
    ]);
    const central = concat([
      u32(0x02014b50),
      u16(20),
      u16(20),
      u16(0),
      u16(0),
      u16(0),
      u16(0),
      u32(crc),
      u32(data.length),
      u32(data.length),
      u16(nameBytes.length),
      u16(0),
      u16(0),
      u16(0),
      u16(0),
      u32(0),
      u32(offset),
      nameBytes,
    ]);
    locals.push(local);
    centrals.push(central);
    offset += local.length;
  }

  const centralDir = concat(centrals);
  const end = concat([
    u32(0x06054b50),
    u16(0),
    u16(0),
    u16(Object.keys(files).length),
    u16(Object.keys(files).length),
    u32(centralDir.length),
    u32(offset),
    u16(0),
  ]);
  const bytes = concat([...locals, centralDir, end]);
  return new Blob([bytes as BlobPart], { type: "application/zip" });
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function exportProjectZip(
  projectId: number,
  preloaded?: LessonContent,
): Promise<void> {
  let content = preloaded;
  if (!content) {
    const lesson = await api.lesson(projectId);
    content = lesson?.content;
  }
  if (!content) throw new Error("No lesson to export yet — run Generate first.");

  let sources: unknown[] = [];
  try {
    sources = await api.sources(projectId);
  } catch {
    /* optional on Vercel cold start */
  }

  let qc1: QCReport | null = null;
  let qc2: QCReport | null = null;
  try {
    qc1 = await api.qc(projectId, 1);
  } catch {
    /* optional */
  }
  try {
    qc2 = await api.qc(projectId, 2);
  } catch {
    /* optional */
  }

  const files: Record<string, string> = {
    "lesson.md": lessonToMarkdown(content),
    "lesson.html": lessonToHtml(content),
    "references.json": JSON.stringify(sources, null, 2),
    "qc_layer1_report.md": qcToMarkdown(qc1, 1),
    "qc_layer2_report.md": qcToMarkdown(qc2, 2),
  };
  downloadBlob(buildZip(files), `chalkproof_${projectId}.zip`);
}

export function downloadLessonFile(content: LessonContent, kind: "md" | "html") {
  const text = kind === "md" ? lessonToMarkdown(content) : lessonToHtml(content);
  const mime = kind === "md" ? "text/markdown" : "text/html";
  const name = kind === "md" ? "lesson.md" : "lesson.html";
  downloadBlob(new Blob([text], { type: mime }), name);
}
