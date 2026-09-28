# Sentinel Implementation Guide

This document describes the implemented system. The architecture documents remain useful product design context; this guide is the operational source of truth.

## Runtime modes

Sentinel selects providers from environment variables and reports the active choice at `GET /api/health` and in the console header.

| Configuration | Memory | Analysis | Intended use |
|---|---|---|---|
| No API keys | In-process memory | Grounded deterministic rules | Development, tests, and an offline fallback |
| `HINDSIGHT_API_KEY` only | Hindsight Cloud | Grounded deterministic rules | Memory integration testing without LLM spend |
| `GROQ_API_KEY` only | In-process memory | Groq JSON mode | Prompt and response-contract testing |
| `GEMINI_API_KEY` only | In-process memory | Gemini JSON mode | Alternate live model testing |
| Hindsight + Groq | Hindsight Cloud | Groq JSON mode + Pydantic validation | Live hackathon demo |
| Hindsight + Groq + Gemini | Hindsight Cloud | Groq primary with Gemini failover | Resilient live demo |

Set `HINDSIGHT_BASE_URL=http://localhost:8888` to use a local Hindsight deployment without a cloud key.

## Backend design

- `schemas.py` rejects unknown fields and validates confidence ranges, incident IDs, severities, and tag uniqueness.
- `memory_client.py` provides the local and Hindsight adapters. Retains use stable `document_id` values, making seeding idempotent.
- `groq_client.py` and `gemini_client.py` validate JSON-mode responses with Pydantic and reject citations that were not present in recall results. Groq is primary; Gemini is optional failover.
- `store.py` persists canonical incident records and retained-memory IDs in SQLite.
- `orchestrator.py` builds the recall query, retrieves evidence, conditionally loads the configured mental model, and invokes analysis.
- `demo.py` replays only incidents 1–5. Each alert is analyzed before its resolution is retained, preserving the learning curve.
- `main.py` exposes REST controls and a WebSocket analysis endpoint.

The current Hindsight API uses `types` in recall requests. Mental models are explicitly created with a stable ID; they are not an implicit unscoped summary. Sentinel creates `checkout-redis-pattern` during seeding and only supplies a mental model to analysis when at least two relevant memories were recalled, preventing stale context from contaminating a cold reset.

## API surface

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Status, version, and active provider modes |
| `POST` | `/api/analyze` | Analyze an arbitrary validated alert |
| `POST` | `/api/incidents` | Retain and persist a resolved incident |
| `GET` | `/api/incidents` | List canonical resolved incidents |
| `POST` | `/api/demo/reset` | Clear demo memory and SQLite state |
| `POST` | `/api/demo/step` | Analyze, return, and retain the next scripted incident |
| WebSocket | `/ws/analyze` | Receive alerts and return status plus structured analysis events |

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

## Verification

From the repository root:

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m ruff check backend
python -m ruff format --check backend
python -m pytest
```

From `frontend`:

```powershell
npm ci
npm run lint
npm run typecheck
npm test
npm audit
npm run build
```

The backend tests validate corpus invariants, Hindsight HTTP contracts, SQLite upserts, and the full five-step API learning curve. The frontend tests cover user-facing formatting; the production build supplies the broader React and TypeScript integration check.

## Demo integrity

Local mode is clearly labeled `local / grounded-rules`; it is never presented as a live Hindsight or Groq result. For the judged integration demo, configure both keys, seed the bank, confirm `/api/health` reports `hindsight / groq`, reset, and then run the five incidents in order.
