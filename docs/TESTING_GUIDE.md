# Sentinel Testing Guide

This is the repeatable verification path for the complete Sentinel application. Run
commands from the repository root unless a command changes directory explicitly.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
Set-Location frontend
npm ci
Set-Location ..
```

Never commit `backend/.env`, `frontend/.env.local`, API keys, SQLite files, or build output.

## Configure providers

For offline development, leave provider keys empty. Sentinel uses local memory and the
deterministic `grounded-rules` analyzer.

For live mode, copy `backend/.env.example` to `backend/.env` and set Hindsight and Groq
keys. The default Groq model is `openai/gpt-oss-120b`. Set `GEMINI_API_KEY` optionally;
Groq is tried first and Gemini is used as backup after a Groq HTTP or contract failure.

## Run backend and frontend

Backend terminal:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
Set-Location frontend
Copy-Item .env.example .env.local -ErrorAction SilentlyContinue
npm run dev
```

Open `http://localhost:3000`, then check backend health:

```powershell
Invoke-RestMethod http://localhost:8000/api/health | ConvertTo-Json -Depth 5
```

Expected status is `ok`. Provider values may be `local`/`grounded-rules` offline,
`hindsight`/`groq` live, or Gemini when only Gemini is configured.

## Frontend walkthrough

1. Open `http://localhost:3000` or `http://127.0.0.1:3000`.
2. Confirm the top-right status says **Command channel online** and shows the configured providers.
3. To guarantee a cold demo, click **Reset memory**. This clears the configured Hindsight test bank.
4. Click **Run incident 1**, wait for the analysis, then inspect the alert, recommended action, and memory evidence panels.
5. Continue with the next incident button until the sequence reads `5/5`. The scenario rail tracks backend progress even after a page refresh.
6. If an error banner appears, keep it visible and inspect the backend terminal; do not repeatedly click the button while it is analyzing.

## Manual incident and history workflow

1. In the **Manual intake** panel, enter a title, service, severity, at least one signal, root cause, and mitigation.
2. Select **Save incident to memory**.
3. Confirm the incident appears in the **Incident ledger**.
4. Select it in the ledger and verify its service, signals, root cause, mitigation, and MTTR details appear.
5. Run a later alert for the same service to let Sentinel recall the newly retained record.

## Seed live memory

Only run this with Hindsight credentials configured:

```powershell
python -m backend.seed_incidents
```

Expected output: `Seeded 9 incidents and 2 world facts.` Seeding is idempotent because
stable incident IDs are used as Hindsight document IDs.

## Test direct analysis

```powershell
$alert = (Get-Content data\incidents.json -Raw | ConvertFrom-Json).incidents[0].alert
$body = $alert | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/analyze `
  -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 10
```

The response must contain `alert`, `response`, `recalled_memories`, and `mental_model`.
With seeded live memory, this checkout alert should normally classify as `KNOWN_PATTERN`
and cite only IDs present in `recalled_memories`.

## Run the five-step demo

Use **Reset memory** and **Run incident** in the console, or:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/demo/reset
1..5 | ForEach-Object {
  Invoke-RestMethod -Method Post http://localhost:8000/api/demo/step |
    ConvertTo-Json -Depth 10
}
```

Reset clears the configured memory bank; use a dedicated test bank for shared accounts.

## Automated checks

```powershell
python -m ruff format --check backend
python -m ruff check backend
python -m pytest
Set-Location frontend
npm run lint
npm run typecheck
npm test
npm run build
Set-Location ..
```

Every command must exit with code 0. Backend tests cover Hindsight request shape,
transient-5xx retry, Gemini validation, and Groq-to-Gemini failover.

## Docker smoke test

```powershell
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://localhost:8000/api/health | ConvertTo-Json -Depth 5
(Invoke-WebRequest http://localhost:3000 -UseBasicParsing).StatusCode
docker compose logs --tail=100 backend frontend
docker compose down
```

Health and frontend status should both be 200. `docker compose down` preserves the
named SQLite volume.

## Troubleshooting

- Port 8000 or 3000 is busy: inspect the existing process before starting another copy.
- UI says Connecting: use `http://localhost:3000` and align `CORS_ORIGINS` exactly.
- Hindsight returns 401/404: verify the key, bank ID, base URL, then reseed.
- Groq is unavailable: confirm `GROQ_MODEL` is supported and set `GEMINI_API_KEY` for backup.
- Never paste API keys into logs, issues, commits, or screenshots.
