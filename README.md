# Chalkproof

Local AI Lesson Creation Tool. Give it a **lesson title** and **learning objective**; it researches sources, generates a structured 45-minute lesson with grounded claims, runs two independent QC audits, and lets you review, edit, preview, and export.

Functionality and research quality over visual polish. Runs entirely on your machine.

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
   ┌──────────┐  httpbin sandbox (Phase 2)
   │EXECUTABLE│
   └────┬─────┘
        ▼
   ┌────┐  QC_MODEL (factual)     ┌────┐  QC_MODEL (instructional)
   │QC1 │  quote match + plag     │QC2 │  alignment + student sim
   └─┬──┘  (never sees QC2)       └─┬──┘  (never sees QC1)
     └──────────┬───────────────────┘
                ▼
        Editor / Preview / Export ZIP
```

Each pipeline step is its own API endpoint, persisted in SQLite, and **individually retryable**. Instructor edits create new `LessonVersion` rows and are never overwritten by regeneration.

---

## Architecture (text)

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

## Setup

### 1. Environment

```bash
cp .env.example .env
# Edit .env — set at least one LLM provider key for full AI generation/QC.
# GENERATOR_MODEL and QC_MODEL must be different models (ideally different providers).
#
# Without keys the app auto-enters demo mode: real research (MDN/Open Library/etc.),
# fixture lessons, programmatic QC1 (quote match + plagiarism), demo QC2, sandbox, export.
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

**Two-command daily run** (after first setup):

```bash
# terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend && npm run dev
```

Optional APIs improve research quality (all degrade gracefully if missing):

| Variable | Purpose |
|---|---|
| `TAVILY_API_KEY` | Preferred web search (else DuckDuckGo) |
| `YOUTUBE_API_KEY` | YouTube search (else DDG site:youtube.com) |
| `GOOGLE_BOOKS_API_KEY` | Extra book metadata |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` | LLM providers |

---

## Usage

1. Enter title + objective (whitespace-only rejected).
2. On the project page, **Run all pending** or run steps one-by-one.
3. Failed steps show an error and a **Retry** button — completed steps are skipped.
4. Edit blocks in the editor (autosave + manual save). Watch the minutes meter vs 45.
5. Open QC tabs: Accept / Reject / Edit-then-apply suggested fixes (diff shown first).
6. Preview the lesson; export ZIP (`lesson.md`, `lesson.html`, `references.json`, both QC reports).
7. **Plant error demo** injects a false claim (`401 is a 5xx`) so you can re-run QC1 and see it caught.

### Samples (end-to-end)

Requires working LLM keys in `.env`:

```bash
cd backend && source .venv/bin/activate
python scripts/run_samples.py
```

Outputs land in `samples/<slug>/`. Fill in `samples/VERIFICATION.md` for manual fact-checks.

### Unit tests

```bash
cd backend && source .venv/bin/activate
pytest -q
```

---

## Tech decisions and why

| Decision | Why |
|---|---|
| **Two different models** (`GENERATOR_MODEL` ≠ `QC_MODEL`) | QC independence — the auditor should not share the generator’s blind spots. Prefer different providers when possible. |
| **Claim → quote grounding** | Every factual sentence stores `{claim, source_id, supporting_quote}`; QC1 programmatically checks the quote exists in fetched text, then LLM-checks semantic support. |
| **Time budgeting ±2 min** | Lessons must fit a 45-minute class; validator rebalances block minutes if the model drifts. |
| **Per-step retry + versioning** | Network/LLM failures are common; never lose instructor edits. Each AI gen, QC apply, and manual save creates a `LessonVersion`. |
| **QC1 ⟂ QC2** | Separate system prompts; QC2 never receives QC1 output. Same `QC_MODEL` role, never the generator. |
| **Graceful research degradation** | If a page/transcript/API fails, continue with remaining sources and note it for QC1. |

---

## Limitations

- Research quality depends on available API keys and network access.
- Book sources are metadata/snippets, not full book text.
- Video relevance uses transcripts; videos without transcripts are marked **unverified**.
- Executable sandbox currently targets HTTP-style topics via `httpbin.org`.
- LLM JSON can still fail after retries — the step is marked failed and retryable.
- N-gram plagiarism guard is heuristic (not a full originality service).

---

## External resources and AI tools used

**APIs / services**

- OpenAI Chat Completions API
- Anthropic Messages API
- Google Gemini generateContent API
- Tavily Search API (optional)
- DuckDuckGo Search (fallback)
- Open Library Search API
- Google Books API (optional)
- YouTube Data API v3 (optional)
- httpbin.org (executable examples)

**Libraries**

- FastAPI, Uvicorn, SQLModel, Pydantic, httpx, python-dotenv
- trafilatura (page extraction)
- youtube-transcript-api
- rapidfuzz (fuzzy quote match)
- React, Vite, react-router-dom
- pytest

**AI assistants**

- Cursor AI assistant (Composer) — used to scaffold and implement this repository

---

## Repo layout

```
backend/          FastAPI app, tests, sample runner
frontend/         React + Vite UI
samples/          E2E outputs + VERIFICATION.md
.env.example      Configuration template
README.md         This file
```
