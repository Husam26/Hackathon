# Backend — Sentinel (FastAPI)

Python + FastAPI service implementing the agent loop. See `../docs/ARCHITECTURE.md` (§2 agent loop, §6 build order) and `../docs/HINDSIGHT_INTEGRATION.md`.

## Modules to build (in order)
| File | Responsibility |
|------|----------------|
| `schemas.py` | Pydantic contracts (`Alert`, `SentinelResponse`, `RecalledMemory`, `IncidentRecord`) — see `docs/DATA_MODEL.md` §2 |
| `memory_client.py` | Hindsight wrapper: `retain`, `recall`, `reflect`, `get_mental_model` |
| `groq_client.py` | Groq chat + JSON/structured output |
| `store.py` | SQLite (SQLModel) system-of-record |
| `orchestrator.py` | alert → recall → mental_model → prompt → Groq → retain |
| `main.py` | FastAPI REST + WebSocket + demo control endpoints (`/reset`, `/step`) |
| `seed_incidents.py` | Load `../data/incidents.json` and `retain` historical incidents |

## Run
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env      # add keys
python seed_incidents.py
uvicorn main:app --reload
```
