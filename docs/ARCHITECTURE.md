# Architecture & Tech Stack

## 1. System overview

Sentinel is an AI Incident Commander. When a production alert fires, it **recalls** similar past incidents from Hindsight, reasons over them with a fast LLM (Groq), returns a structured triage/diagnosis, and after resolution **retains** the new incident so the system keeps learning.

```
                         ┌──────────────────────────────────────────┐
                         │                FRONTEND                    │
                         │   Next.js + Tailwind + shadcn/ui           │
                         │   ┌───────────┐   ┌──────────────────┐     │
                         │   │ Chat Pane │   │  🧠 Memory Panel  │     │
                         │   │ (incident)│   │ recalled memories │     │
                         │   └───────────┘   │ + recall scores   │     │
                         │   ┌──────────────┐└──────────────────┘     │
                         │   │  MTTR Chart  │  Demo Controls           │
                         │   └──────────────┘  (seed / reset / step)   │
                         └───────────────▲──────────────┬─────────────┘
                                         │ WebSocket / REST
                         ┌───────────────┴──────────────▼─────────────┐
                         │                BACKEND (FastAPI)            │
                         │                                             │
                         │   main.py         ── WS + REST endpoints    │
                         │   orchestrator.py ── the agent loop         │
                         │   memory_client.py── Hindsight wrapper      │
                         │   groq_client.py  ── Groq wrapper (JSON)    │
                         │   schemas.py      ── Pydantic contracts     │
                         │   store.py        ── SQLite system-of-record│
                         └───────┬─────────────────────────┬──────────┘
                                 │                          │
                    ┌────────────▼──────────┐   ┌───────────▼───────────┐
                    │   Hindsight (memory)  │   │      Groq (LLM)       │
                    │  retain / recall /    │   │  llama-3.3-70b        │
                    │  reflect / mental-model│   │  JSON / structured    │
                    └───────────────────────┘   └───────────────────────┘
```

## 2. The agent loop (orchestrator.py)

For every incoming alert:

1. **Build query** from the alert signature (service, symptoms, time, recent deploys).
2. **`recall`** similar memories from Hindsight (scoped by `service:*` tags; spreading activation surfaces cross-service links).
3. **`getMentalModel`** (when a pattern exists) — Hindsight's own auto-synthesized summary of the recurring signature. *This drives the "genius moment."*
4. **Compose prompt** — inject recalled memories + mental model as authoritative context (see `docs/HINDSIGHT_INTEGRATION.md`).
5. **Groq call** with JSON/structured output → `SentinelResponse`.
6. **Stream** the response to the UI over WebSocket.
7. On resolution, **`retain`** the incident as an `experience` memory (+ optional `world` facts).

## 3. Tech stack rationale

| Layer | Choice | Why |
|-------|--------|-----|
| LLM | **Groq**, `llama-3.3-70b-versatile`, JSON mode | Hackathon-recommended; sub-second latency makes incident triage feel real. |
| Memory | **Hindsight Cloud** (`api.hindsight.vectorize.io`); local Docker (`:8888`) fallback | Zero infra; Docker fallback protects the demo against flaky wifi. |
| Backend | **Python + FastAPI** | Fastest path to a clean REST/WS API; first-class Hindsight + Groq Python SDKs; async fits streaming. |
| System of record | **SQLite** (SQLModel) | Zero-setup canonical store for full postmortems, PR links, runbooks. Hindsight is the recall layer, not the DB of record. |
| Frontend | **Next.js + Tailwind + shadcn/ui** | Professional SaaS look with almost no custom CSS. |
| Realtime | **WebSocket / SSE** | Streams the agent "thinking" token-by-token. |
| Deploy | Vercel (FE) + Render/Fly.io or **ngrok** (BE) | ngrok is fastest for a live stage demo. |

## 4. The two design bets

1. **The Memory Panel is the whole pitch.** Left = incident chat; right = "🧠 Hindsight Memory" showing recalled incidents + recall scores (empty & dim in INC-1, dense & glowing in INC-5); bottom = MTTR trend dropping 90→3 min. Judges *watch memory work*.
2. **Deterministic demo, real intelligence.** Pre-seeded alerts + a reset button = repeatable on stage — but every response is a *real* Groq call over *real* Hindsight recall. Nothing is faked.

## 5. Multi-tenancy

One Hindsight **memory bank per team/tenant** (e.g. `bank_id = "acme-sre"`). Bank isolation gives us multi-tenant separation for free — good for the "real SaaS product" story.

## 6. Build order

Do it in this order — each step depends on the one before:

1. **`data/incidents.json`** — the synthetic corpus (INC-1→5 + distractors). Everything depends on this. See `docs/DATA_MODEL.md`.
2. **`backend/schemas.py`** — Pydantic models: `Alert`, `IncidentRecord`, `SentinelResponse`, `RetainPayload`, `RecallQuery`.
3. **`backend/memory_client.py`** — Hindsight wrapper (`retain`, `recall`, `reflect`, `get_mental_model`). See `docs/HINDSIGHT_INTEGRATION.md`.
4. **`backend/groq_client.py`** — Groq chat + JSON-mode structured output.
5. **`backend/store.py`** — SQLite system-of-record.
6. **`backend/orchestrator.py`** — the agent loop above.
7. **`backend/main.py`** — FastAPI REST + WebSocket + demo control endpoints.
8. **`backend/seed_incidents.py`** — loads `data/incidents.json` and `retain`s the historical incidents.
9. **`frontend/`** — ops console: `ChatPane`, `MemoryPanel`, `MTTRChart`, `DemoControls`.

## 7. Environment variables

| Var | Used by | Notes |
|-----|---------|-------|
| `GROQ_API_KEY` | groq_client | From console.groq.com |
| `GROQ_MODEL` | groq_client | Default `llama-3.3-70b-versatile` |
| `HINDSIGHT_API_KEY` | memory_client | From Hindsight Cloud |
| `HINDSIGHT_BASE_URL` | memory_client | Cloud: `https://api.hindsight.vectorize.io`; local: `http://localhost:8888` |
| `HINDSIGHT_BANK_ID` | memory_client | e.g. `acme-sre` |
| `DATABASE_URL` | store | Default `sqlite:///./sentinel.db` |

Never commit `.env` — only `.env.example`.
