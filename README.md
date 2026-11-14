# Chalkproof

Local AI Lesson Creation Tool. Give it a **lesson title** and **learning objective**; it researches sources, generates a structured 45-minute lesson with grounded claims, runs **two independent QC audits**, and lets you review, edit, preview, and export.

> **Pitch:** Most AI lesson tools just generate text. Chalkproof forces claims to sources, audits facts and teaching quality separately, and keeps the instructor in control of every fix.

Live demo (ephemeral DB / may hit timeouts): [chalkproof.vercel.app](https://chalkproof.vercel.app)  
Recommended for demos/interviews: run **locally** (below).

---

## Overview

```
Title + Objective
        │
        ▼
   ┌─────────┐   web / books / YouTube
   │ RESEARCH│──────────────────────────► Sources (tiered)
   └────┬────┘
        ▼
   ┌─────────┐   GENERATOR_MODEL
   │ GENERATE│──────────────────────────► Lesson JSON + Claims
   └────┬────┘
        ▼
   ┌──────────┐  httpbin sandbox (when HTTP-related)
   │EXECUTABLE│
   └────┬─────┘
        ▼
   ┌────┐  QC_MODEL (factual)     ┌────┐  QC_MODEL (instructional)
   │QC1 │  quote match + plag     │QC2 │  alignment + student sim
   └─┬──┘  (never sees QC2)       └─┬──┘  (never sees QC1)
     └──────────┬───────────────────┘
                ▼
        Editor / Preview / Export PDF · ZIP
```

Each pipeline step is its own API endpoint, persisted in SQLite, and **individually retryable**. Instructor edits create new `LessonVersion` rows and are never overwritten by regeneration.

---

## What are QC audits?

**QC = quality control** on the generated lesson before you trust it.

| Layer | Question it answers | Checks |
|---|---|---|
| **QC1 — Factual** | Is this true and grounded? | Claim↔quote match in source text, semantic support, plagiarism n-grams, weak/irrelevant sources, executable flags |
| **QC2 — Instructional** | Is this good teaching? | Objective alignment, clarity/structure, gaps in explanations/examples/practicals, ~45 min time budget, knowledge-check quality, student simulator |

They are **independent**: QC2 never sees QC1’s output. Both use `QC_MODEL`, never `GENERATOR_MODEL`.  
If the LLM is rate-limited, QC still returns partial programmatic checks instead of crashing the pipeline.

---

## UI guide (what each option means)

### Home
| Control | Meaning |
|---|---|
| **Lesson title** | Topic name for the lesson |
| **Learning objective** | What learners should be able to do afterward |
| **Create project** | Creates a DB project + pipeline steps set to `pending` (rejects empty/whitespace) |

### Project header
| Control | Meaning |
|---|---|
| **Status** | `created` → in progress → `ready` when finished; `failed` if a step failed (other steps kept) |
| **Preview** | Read-only rendered lesson |
| **Export PDF** | Downloads a printable lesson PDF (title, objective, blocks, answer key) |
| **Export ZIP** | Downloads `lesson.md`, `lesson.html`, `references.json`, both QC reports |

### Pipeline tab
| Control | Meaning |
|---|---|
| **research** | Gather web/books/videos, extract text, assign reliability tiers; videos without transcripts = unverified |
| **generate** | Build ~45-min structured lesson + claim ledger via `GENERATOR_MODEL` |
| **executable** | Run real HTTP demos (httpbin) when topic fits; otherwise mark not applicable |
| **qc1** | Factual audit |
| **qc2** | Instructional audit |
| **Run** | Re-run that step only |
| **Retry** | Same as Run when status is `failed` |
| **Run all pending** | Run unfinished steps in order; **skips** already `done` steps |
| **Re-run all** | Force every step again from research |

### Editor tab
| Control | Meaning |
|---|---|
| Block **title / content / minutes** | Edit lesson structure and timing |
| **Minutes meter** | Sum of block minutes vs 45 (±2); warns if off target |
| **Save now / autosave** | Creates a new instructor `LessonVersion` |

### Sources tab
| Column | Meaning |
|---|---|
| **Type** | `web` / `book` / `video` |
| **Tier** | `high` (official docs), `medium`, `low` |
| **Claims** | How many lesson claims cite this source |
| **Notes** | Video timestamps or “unverified — no transcript” |

### QC tab
| Control | Meaning |
|---|---|
| **Layer 1 — Factual** | Fact/grounding issues |
| **Layer 2 — Instructional** | Teaching-quality issues |
| **Accept** | Apply suggested fix to the lesson (new version) |
| **Reject** | Dismiss the issue |
| **Review / diff** | Before vs suggested text; edit then apply |
| **Plant error demo** | Injects a known false claim (e.g. “401 is a 5xx”); re-run QC1 to show it gets caught |

### Versions tab
| Control | Meaning |
|---|---|
| Version list | History of AI gens, QC applies, and manual saves |
| **Restore** | Roll back by creating a new instructor version from an older one |

---

## Demo / interview walkthrough (~6–8 min)

1. **Pitch** — grounded lesson generation + dual QC + instructor control  
2. **Create** a clear title + objective (or open a finished project)  
3. **Pipeline** — show per-step status / retry design  
4. **Sources** — tiers and evidence  
5. **Editor** — 45-min meter + versioned saves  
6. **QC** — Layer 1 then Layer 2; Accept/Reject one issue; optional Plant error  
7. **Preview + Export PDF / ZIP**

**If a live LLM call fails:** open a finished project’s Preview and explain retries/versioning — that still demonstrates the product.

---

## Architecture

```
frontend/ (React + Vite)
  Home → create project
  Project → pipeline | editor | sources | QC tabs | versions
  Preview → rendered lesson + downloads

backend/ (FastAPI + SQLModel/SQLite)
  routers/     HTTP API
  services/    research, generate, sandbox, qc1, qc2, export, llm
  models/      Project, Source, LessonVersion, Claim, QCReport, StepStatus
  utils/       time_budget, quote_match, plagiarism
```

---

## Setup (local — recommended)

### 1. Environment

```bash
cp .env.example .env
# Set GROQ_API_KEY (or another provider).
# GENERATOR_MODEL and QC_MODEL must be different models.
# Example (Groq):
#   GENERATOR_MODEL=groq:openai/gpt-oss-120b
#   QC_MODEL=groq:openai/gpt-oss-20b
#
# Without keys the app auto-enters demo mode (fixture lesson + programmatic QC).
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

**Daily run:**

```bash
# terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend && npm run dev
```

### Optional research APIs

| Variable | Purpose |
|---|---|
| `TAVILY_API_KEY` | Preferred web search (else DuckDuckGo / curated fallbacks) |
| `YOUTUBE_API_KEY` | YouTube search |
| `GOOGLE_BOOKS_API_KEY` | Extra book metadata |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` / `XAI_API_KEY` / `GROQ_API_KEY` | LLM providers |

---

## Deploy on Vercel

Frontend + FastAPI under `/api/*` (Python serverless).

```bash
npm i -g vercel
vercel link
vercel env add GROQ_API_KEY
vercel env add GENERATOR_MODEL
vercel env add QC_MODEL
vercel --prod
```

**Limits:** SQLite is ephemeral (`/tmp`); long pipeline runs may time out on Hobby. Prefer local for interviews.

---

## Usage checklist

1. Enter title + objective  
2. **Run all pending** or run steps one-by-one  
3. Failed steps → **Retry** (completed steps stay done)  
4. Edit in **editor**; watch minutes vs 45  
5. **qc** → Accept / Reject / Review diff  
6. **Preview** + **Export PDF** / **Export ZIP**  
7. Optional: **Plant error demo** → re-run QC1  

### Samples

```bash
cd backend && source .venv/bin/activate
python scripts/run_samples.py
```

Outputs: `samples/<slug>/`. Manual fact-check table: `samples/VERIFICATION.md`.

### Unit tests

```bash
cd backend && source .venv/bin/activate
pytest -q
```

---

## Tech decisions and why

| Decision | Why |
|---|---|
| **Two different models** | QC shouldn’t share the generator’s blind spots |
| **Claim → quote grounding** | Every fact stores `{claim, source_id, supporting_quote}`; QC1 checks the quote exists in source text |
| **Time budgeting ±2 min** | Fits a class period; rebalance if the model drifts |
| **Per-step retry + versioning** | Failures are common; never lose instructor edits |
| **QC1 ⟂ QC2** | Separate prompts; QC2 never receives QC1 output |
| **Graceful degradation** | Search/LLM failures continue with remaining work and partial reports |

---

## Limitations

- Research quality depends on network/API keys; curated fallbacks cover common topics (HTTP, React, maths, etc.)
- Book sources are metadata/snippets, not full text
- Videos without transcripts are marked **unverified**
- Executable sandbox targets HTTP-style topics (`httpbin.org`)
- Vercel: ephemeral DB + possible function timeouts
- Plagiarism guard is n-gram heuristic, not a full originality service

---

## External resources and AI tools used

**APIs / services:** OpenAI, Anthropic, Google Gemini, Groq, xAI (optional), Tavily (optional), DuckDuckGo, Open Library, Google Books (optional), YouTube Data API (optional), httpbin.org  

**Libraries:** FastAPI, Uvicorn, SQLModel, Pydantic, httpx, trafilatura, youtube-transcript-api, rapidfuzz, React, Vite, react-router-dom, pytest  

---

## Repo layout

```
backend/          FastAPI app, tests, sample runner
frontend/         React + Vite UI
api/              Vercel Python entrypoint
samples/          E2E outputs + VERIFICATION.md
vercel.json       Vercel build/rewrite config
.env.example      Configuration template
README.md         This file
```
