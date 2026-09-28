# Local Development Setup

## Prerequisites

- Python 3.11+
- Node.js 22+
- Optional: Docker Desktop
- Optional for live mode: Groq, Gemini, and Hindsight API keys

## Backend

Run from the repository root so the `backend` package and `data` directory resolve consistently.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
Copy-Item backend\.env.example backend\.env  # optional
python -m uvicorn backend.main:app --reload
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

With no keys, the response reports `local` memory and `grounded-rules` analysis. That mode is complete enough to run and test the five-step demo offline.

## Frontend

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Live provider setup

Edit `backend/.env`:

```dotenv
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
# Optional backup provider; used if Groq has an HTTP or response-contract failure
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.6-flash
HINDSIGHT_API_KEY=hsk_...
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
HINDSIGHT_BANK_ID=acme-sre
HINDSIGHT_MENTAL_MODEL_ID=checkout-redis-pattern
DATABASE_URL=sqlite:///./backend/sentinel.db
CORS_ORIGINS=http://localhost:3000
```

Seed the complete corpus and explicitly provision the mental model:

```powershell
python -m backend.seed_incidents
```

Seeding is idempotent because each incident uses its stable ID as Hindsight's `document_id`.

## Demo flow

1. Start backend and frontend.
2. Confirm the provider labels in the header match the intended mode.
3. Select **Reset memory** before a new presentation.
4. Run incidents 1–5 in order.
5. On step 5, verify two prior Redis incidents are cited, occurrence count is 3, the mental model is visible, and MTTR reads `90 → 15 → 3` for the recurring signature.

## Docker

```powershell
docker compose up --build
```

`backend/.env` is optional. Compose persists SQLite under the `sentinel-data` named volume.

## Troubleshooting

- **UI remains on Connecting:** open the console through `http://localhost:3000` and ensure `CORS_ORIGINS` contains that exact origin.
- **Hindsight returns 401:** check that the key starts with the current Hindsight key format and that it can access the configured bank.
- **Cold reset still looks informed:** confirm the API returned no recalled memories. The orchestrator intentionally withholds mental models until at least two memories are recalled.
- **Groq output is rejected:** inspect backend logs. Sentinel retries once when JSON or citations violate the response contract; with `GEMINI_API_KEY` configured, it then tries Gemini.
- **Port already in use:** identify the existing listener before starting a duplicate process.
