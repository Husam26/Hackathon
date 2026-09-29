# Architecture

## System overview

Sentinel receives an alert, recalls service-scoped evidence, optionally loads the explicitly configured Hindsight mental model, produces a validated structured response, and retains the final incident after resolution.

```text
Next.js operations console
  ├─ REST: health, demo controls, incidents, arbitrary analysis
  └─ WebSocket: status + structured alert analysis
                 │
                 ▼
FastAPI application factory ── API delivery layer ── SentinelOrchestrator
  ├─ MemoryProvider ── Hindsight Cloud with mirrored local fallback
  ├─ IncidentAnalyzer ── Groq primary, Gemini failover, or grounded-rules fallback
  └─ IncidentStore ── SQLite / SQLModel
```

## Request flow

1. Validate the alert with strict Pydantic contracts.
2. Build a query from service, severity, timestamp, signals, and recent deploys.
3. Recall service-scoped `experience`, `world`, and `observation` facts.
4. Load the configured mental model only when at least two memories were recalled.
5. Analyze with Groq, fail over to Gemini for a provider/contract failure when configured, then use deterministic grounded rules as the final safe fallback.
6. Reject malformed output or citations outside the retrieved-memory allow-list.
7. Return the structured analysis and evidence to the console.
8. After resolution, retain the narrative with a stable document ID, mirror it locally when Hindsight is configured, and upsert the canonical SQLite record.

## Why two stores

- **Hindsight** is the semantic recall and consolidated-knowledge layer.
- **SQLite** is the canonical system of record for full incidents, MTTR, runbooks, pull requests, and retained-memory IDs.

The stores are intentionally not interchangeable. Losing the memory index must not erase the postmortem record, and the full canonical record is not injected into every LLM request.

## Grounding rules

- A matching service alone does not establish a known pattern.
- The fallback analyzer compares service, trigger, symptoms, and time window.
- Occurrences are deduplicated by incident/document ID because Hindsight may extract multiple facts from one retained document.
- Groq may cite only IDs returned in the current recall result.
- Empty or weak recall produces `NOVEL` and generic triage rather than invented history.
- Mental models are explicitly created and fetched by ID; stale stored summaries are withheld on cold or weak recall.

## Module map

| Module | Responsibility |
|---|---|
| `backend/schemas.py` | API, corpus, provider, and response contracts |
| `backend/config.py` | Environment settings and defaults |
| `backend/memory_client.py` | Hindsight and local memory adapters |
| `backend/resilience.py` | Provider fallback decorators and local memory mirror |
| `backend/groq_client.py` | Groq and grounded-rules analyzers |
| `backend/store.py` | SQLite system of record |
| `backend/orchestrator.py` | Recall → mental model → analysis → retain flow |
| `backend/demo.py` | Deterministic five-step state machine |
| `backend/services.py` | Runtime dependency graph and provider composition |
| `backend/api.py` | REST and WebSocket delivery layer |
| `backend/app_factory.py` | FastAPI lifecycle, CORS, and router registration |
| `backend/main.py` | Minimal ASGI compatibility entrypoint |
| `backend/seed_incidents.py` | Idempotent corpus and mental-model provisioning |
| `frontend/components/sentinel-console.tsx` | Main incident-command experience |
| `frontend/components/mttr-chart.tsx` | Dependency-free MTTR visualization |

## Deployment

- Local development: Uvicorn on port 8000 and Next.js on port 3000.
- Containers: `docker compose up --build`, with SQLite persisted in a named volume.
- Suggested hosted split: any Python container host for the API and a Next.js-compatible frontend host.

The public browser URL for `NEXT_PUBLIC_API_URL` must be reachable by the user; a Compose service name such as `backend` is not a browser-reachable production URL.
