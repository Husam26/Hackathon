# Sentinel — SRE Incident Commander

Sentinel is a memory-powered incident-response console. It recalls related production incidents, grounds every historical claim in retrieved evidence, recommends proven mitigations, and retains resolved incidents so the next response starts smarter.

The five-step Northwind Pay demo shows the learning curve directly: cold-start triage, an unrelated decoy, a deliberately ambiguous recurrence, a confirmed pattern, and a third-occurrence escalation where MTTR falls from 90 minutes to 3.

## What is implemented

- FastAPI REST and WebSocket backend with strict Pydantic contracts.
- Hindsight Cloud REST adapter plus an explicit offline/local-memory fallback.
- Groq JSON-mode primary analysis with validation, retry, and citation allow-listing, plus optional Gemini failover.
- Grounded deterministic analyzer for tests and keyless development.
- SQLite system of record with idempotent incident upserts.
- Seven-incident synthetic corpus, including five scripted incidents and two distractors.
- Next.js 16 operations console with memory evidence, mental-model status, hypotheses, mitigation, escalation, and MTTR visualization.
- Backend and frontend tests, linting, production builds, Docker Compose, and GitHub Actions CI.

Implementation details and API contracts: [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md).

Judge-facing evidence map: [docs/JUDGING_ALIGNMENT.md](docs/JUDGING_ALIGNMENT.md). Live walkthrough: [docs/LIVE_DEMO_PLAYBOOK.md](docs/LIVE_DEMO_PLAYBOOK.md).

## Quick start — offline mode

Offline mode needs no keys and clearly identifies itself as `local / grounded-rules` in the UI.

```powershell
# Terminal 1 — from the repository root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
python -m uvicorn backend.main:app --reload

# Terminal 2
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000` and use **Run incident** to replay the five-step scenario. Backend OpenAPI documentation is at `http://localhost:8000/docs`.

## Live Hindsight + AI analysis mode

```powershell
Copy-Item backend\.env.example backend\.env
# Add GROQ_API_KEY and HINDSIGHT_API_KEY to backend\.env.
# Optionally add GEMINI_API_KEY for automatic LLM failover.
python -m backend.seed_incidents
python -m uvicorn backend.main:app --reload
```

Before presenting a live integration, check `http://localhost:8000/api/health` reports:

```json
{"status":"ok","providers":{"memory":"hindsight","analysis":"groq"}}
```

The checked-in Groq default is `openai/gpt-oss-120b`, selected because the previously configured Llama model was unavailable for the configured key. Add `GEMINI_API_KEY` to enable `gemini-3.6-flash` as a backup; when both are configured, Groq is tried first and Gemini is used only for a Groq HTTP/contract failure. Sentinel validates every response with Pydantic and rejects citations that were not retrieved from memory.

## Verification

```powershell
# Repository root
python -m ruff check backend
python -m ruff format --check backend
python -m pytest

# frontend\
npm run lint
npm run typecheck
npm test
npm audit
npm run build
```

## Docker Compose

```powershell
# backend/.env is optional; without it the stack uses offline mode
docker compose up --build
```

The frontend runs on port 3000, the API on port 8000, and SQLite data is stored in the `sentinel-data` volume.

## Repository layout

```text
backend/    FastAPI service, providers, SQLite store, demo controller, tests
data/       Validated synthetic incident corpus
docs/       Architecture, integration, scenario, setup, and implementation notes
frontend/   Next.js operations console and tests
.github/    CI workflow
```

## Memory integrity

Hindsight is the recall layer; SQLite is the canonical record. A matching service alone is not treated as a known incident. Sentinel compares service, trigger, symptoms, and time window, deduplicates occurrences by incident/document ID, and requires retrieved-memory citations for claims about historical incidents, tickets, or mitigations.
