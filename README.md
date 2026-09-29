# Sentinel — Incident Memory Command Center

Sentinel is a memory-powered SRE incident-response application built for the moment
an on-call engineer needs a proven answer, not a generic checklist. It recalls prior
incidents with Hindsight, constrains every historical claim to retrieved evidence,
and turns the result into a safe, reviewable operator workflow.

> The product thesis: recurring incidents should get faster and safer to resolve
> because each resolved incident becomes usable operational memory.

## Why this is not a chatbot

A normal incident chatbot can produce plausible advice without knowing whether it
worked before. Sentinel separates the operational responsibilities:

- **Hindsight** recalls semantic operational experience, scores it, and exposes the
  source memories.
- **SentinelOrchestrator** builds context, applies optional recency/severity bias,
  retrieves a mental model only when evidence is strong enough, and enforces
  citation grounding.
- **Groq → Gemini → grounded rules** returns validated structured triage without
  allowing an unavailable or malformed AI provider to crash the operator console.
- **SQLite** keeps the canonical audit record even if the memory provider is
  unavailable.
- **The operator** remains responsible for external action: Teams, GitHub, and
  runbook controls create safe handoffs, never production commands.

## Reviewer journey

1. Open `/demo` for the five-step Northwind Pay learning curve. It shows cold
   triage, a decoy, ambiguous evidence, a confirmed recurrence, and an escalation
   where synthetic MTTR improves from `90 → 15 → 3` minutes.
2. Open recalled Hindsight cards and the Memory Inspector to see IDs, final score,
   retrieval-stage scores, citations, and Memory Impact.
3. Use **Compare with cold LLM triage** to contrast generic advice with grounded,
   evidence-backed response.
4. Change recency and severity controls to bias Hindsight retrieval without
   replacing semantic ranking.
5. Open `/manual` to document a resolved incident or reopen any ledger record in
   the same command workspace, then show its Teams, GitHub Issue, runbook, and
   related PR/runbook navigation.
6. Paste an Azure Monitor Common Alert Schema payload and show it enter the same
   full analysis workspace.

## Workspaces

| Route | Purpose | What to show |
| --- | --- | --- |
| `/demo` | Scripted five-step learning curve | Evidence, cold-vs-memory comparison, mental model, MTTR trend |
| `/manual` | Manual incident documentation and history | Analyze-before-retain, ledger replay, artifacts, enterprise handoffs |

Both workspaces use the same **Hindsight retrieval controls**, **Proof of memory**,
**Live command thread**, **Hindsight evidence**, **resolution velocity**, and safe
enterprise-handoff controls.

## Architecture

```text
Next.js Console (/demo and /manual)
        │ REST / WebSocket
        ▼
FastAPI application factory
  └─ backend/http/routes
      ├─ system + architecture endpoint
      ├─ analysis + Azure + Teams + GitHub + runbook routes
      ├─ incident + manual + artifact routes
      ├─ demo routes
      └─ WebSocket route
        │
        ▼
SentinelOrchestrator
  ├─ Hindsight Cloud with local mirrored fallback
  ├─ Groq → Gemini → grounded-rules analyzer chain
  └─ SQLite canonical incident store
```

The complete, current Mermaid sequence and system diagrams are available through:

```text
GET /api/architecture/workflow
```

They are also rendered in [Workflow diagrams](docs/WORKFLOW_DIAGRAMS.md). See
[Architecture](docs/ARCHITECTURE.md) for module responsibilities.

## Synthetic demo and seed data

The checked-in corpus contains **9 incidents and 2 world facts**:

- Five ordered incidents for the guided learning curve.
- Two distractors to demonstrate that Sentinel does not overclaim similarity.
- An Azure Monitor checkout recurrence with a pre-filled Issue, PR, runbook, and
  JIRA reference.
- A Manual Intake cache-capacity regression with retention tags and artifact
  navigation.

Seed data is synthetic and safe for a dedicated demo bank. Seeding is idempotent
because each record has a stable incident/document ID.

```powershell
python -m backend.seed_incidents
# Expected: Seeded 9 incidents and 2 world facts.
```

## Quick start — offline mode

Offline mode requires no external keys. It uses local memory and deterministic
grounded rules, which makes it the reliable rehearsal mode.

```powershell
# Terminal 1 — repository root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2
Set-Location frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open `http://127.0.0.1:3000`. The root URL redirects to `/demo`; select **Manual**
in the navigation to switch workspaces. API documentation is at
`http://127.0.0.1:8000/docs`.

## Live Hindsight + AI mode

```powershell
Copy-Item backend\.env.example backend\.env
```

Configure a dedicated bank in `backend/.env`:

```dotenv
HINDSIGHT_API_KEY=...
HINDSIGHT_BANK_ID=your-dedicated-demo-bank
GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-120b
# Optional backup provider
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.6-flash
```

Then seed and run:

```powershell
python -m backend.seed_incidents
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Confirm the active provider chain before presenting:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health | ConvertTo-Json -Depth 5
```

## Safe enterprise behavior

- **Azure Monitor:** accepts a validated subset of Common Alert Schema and opens the
  result in the standard workspace.
- **Teams:** creates and copies a Teams-ready brief; it does not post to a tenant.
- **GitHub:** opens a pre-filled **new Issue** handoff for the selected incident; it
  does not create an issue, trigger a workflow, or merge code.
- **Runbooks:** require a recorded human confirmation and return an auditable handoff;
  Sentinel never runs `kubectl`, database, or rollback commands.

## Verification

```powershell
# Repository root
python -m ruff check backend
python -m ruff format --check backend
python -m pytest

# Frontend
Set-Location frontend
npm run lint
npm run typecheck
npm test
npm run build
```

## Documentation

- [Live demo playbook](docs/LIVE_DEMO_PLAYBOOK.md)
- [Detailed setup](docs/SETUP.md)
- [Testing guide](docs/TESTING_GUIDE.md)
- [Implementation and API guide](docs/IMPLEMENTATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Workflow diagrams](docs/WORKFLOW_DIAGRAMS.md)
- [Judging alignment](docs/JUDGING_ALIGNMENT.md)

## Repository layout

```text
backend/
  http/routes/       HTTP and WebSocket delivery modules
  workflows/         Versioned Mermaid workflow artifacts
  services.py        Dependency composition root
  orchestrator.py    Recall → reasoning → retention application flow
  memory_client.py   Hindsight and local provider adapters
  resilience.py      Memory/AI fallback behavior
  store.py           SQLite canonical record store
  tests/             API, provider, demo, resilience regression tests
frontend/
  app/demo/          Guided demo workspace
  app/manual/        Manual incident workspace
  components/        Shared command-console UI
  lib/               Typed API client and UI contracts
data/                Validated synthetic incidents and world facts
docs/                Reviewer, architecture, setup, and test material
```