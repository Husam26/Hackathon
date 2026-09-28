# 🛡️ Sentinel — SRE Incident Commander Agent

> An AI incident-response co-pilot with **persistent memory**. It gets smarter with every incident — recognizing recurring patterns, recalling proven fixes, and collapsing Mean-Time-To-Resolution (MTTR) from ~90 minutes to ~3 minutes.

Built for the hackathon on **[Hindsight](https://hindsight.vectorize.io)** (agent memory by Vectorize) + **[Groq](https://groq.com)** (fast LLM inference).

---

## The one-line pitch

Every SRE team re-solves the same production incidents at 3 AM because institutional knowledge lives in senior engineers' heads and in lost Slack threads. **Sentinel remembers.** Without memory it's a generic checklist bot; with Hindsight memory it behaves like the team's most experienced on-call engineer.

## Why this wins

- **Deep technical niche** other teams avoid (real SRE/DevOps workflows, not a chatbot).
- **A visible learning curve** — the demo *shows* the agent improving over 5 incidents.
- **Hindsight is the moat, not a bolt-on** — memory recall & the auto-synthesized "Mental Model" literally drive the agent's best answer (targets the 25% memory-integration criterion).

---

## The "Genius Moment" (Interaction 5)

By the 5th incident, Sentinel — *before any manual investigation* — says:

> 🔴 **Recurring incident detected — 3rd occurrence of a known pattern (INC-1, INC-4, now this).**
> **Root cause:** `payments-service` opens unbounded Redis connections; the `checkout-service` pool saturates.
> **Proven mitigation (worked 2/2):** roll back the payments deploy + `kubectl rollout restart checkout-service`. ETA ~4 min.
> **This should not still be happening** — the permanent fix `JIRA-891` has been open for 6 weeks. Recommend blocking payments deploys until merged.
> 📉 **MTTR for this signature: 90 min → 15 min → ~3 min.**

Full walkthrough: **[docs/DEMO_SCENARIO.md](docs/DEMO_SCENARIO.md)**.

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| LLM inference | **Groq** (`llama-3.3-70b-versatile`, JSON mode) |
| Agent memory | **Hindsight Cloud** (`api.hindsight.vectorize.io`), local Docker fallback |
| Backend | **Python + FastAPI** (REST + WebSocket streaming) |
| System of record | **SQLite** (SQLModel) |
| Frontend | **Next.js + Tailwind + shadcn/ui** (dark "ops console" theme) |
| Deploy | Vercel (frontend) + Render/Fly.io or ngrok (backend) |

Details: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## Repository layout

```
.
├── README.md
├── docs/
│   ├── ARCHITECTURE.md          # System design + tech stack rationale
│   ├── HINDSIGHT_INTEGRATION.md # retain / recall / reflect / mental-model contracts
│   ├── DEMO_SCENARIO.md         # The 5-step learning-curve script
│   ├── DATA_MODEL.md            # Incident + memory schemas
│   └── SETUP.md                 # Local dev setup
├── backend/                     # FastAPI app (see backend/README.md)
├── frontend/                    # Next.js console (see frontend/README.md)
└── data/                        # Synthetic incident corpus
```

---

## Quickstart

See **[docs/SETUP.md](docs/SETUP.md)** for full instructions. TL;DR:

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add GROQ_API_KEY + HINDSIGHT_API_KEY
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Roles

- **Product / Architecture:** planning, demo narrative, Hindsight strategy.
- **Development:** implementation against the specs in `docs/`.

Start with **[docs/SETUP.md](docs/SETUP.md)** → then pick up tasks in the order listed in **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#build-order)**.
