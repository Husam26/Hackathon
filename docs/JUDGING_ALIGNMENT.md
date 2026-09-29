# Sentinel Judging Alignment

This document maps the implemented product to the evaluation rubric without making
claims that exceed the code or the live configuration.

## Innovation — 30%

Sentinel is an incident-memory control plane, not a general chatbot. It separates:

- **Hindsight** for semantic, keyword, graph, and temporal recall of prior operational
  experience;
- **SQLite** for canonical auditable incident records; and
- **a grounded analyzer** that may cite only facts returned by the current recall.

The operator can bias the recall engine by recency and severity while still leaving
Hindsight's semantic engine responsible for ranking. Azure Monitor alert intake, a
Teams-ready brief, GitHub review handoff, and confirmation-gated runbook handoff turn
the analysis into an enterprise workflow instead of a chat transcript.

## Hindsight Memory — 25%

Memory is central to both the product and the demo:

1. Resolved incidents are retained with stable document IDs, structured tags, and event
   timestamps.
2. Future alerts recall service-scoped evidence, optionally temporally biased by an
   operator-selected Hindsight `temporal_window` and severity tags.
3. The response exposes recalled evidence, memory IDs, per-stage scores, citations,
   mental-model state, and a **Memory Impact** record.
4. The **Compare with cold LLM triage** control demonstrates why retrieved history is
   valuable: cold triage remains generic while the memory-grounded path can cite prior
   mitigations and unresolved ticket references.

The live demo playbook intentionally shows memory cards and the inspector before any
integration buttons: memory must be visible within the first 15 seconds.

## Technical Implementation — 20%

- Strict Pydantic request/response contracts reject unknown input fields.
- Provider adapters isolate Hindsight, Groq, Gemini, and local fallbacks.
- Hindsight calls retain item-level tags, use stable IDs, retry transient 5xx errors,
  and map final/reranker scores into the API response.
- Groq can fail over to Gemini and finally deterministic grounded rules. This keeps a
  provider outage from becoming an unhandled console error.
- A human gate records runbook approval but never runs a production command.
- Backend regression tests cover contracts, demo flow, Hindsight retries, manual intake,
  provider fallback, and memory-impact behavior. Frontend lint, types, tests, and build
  are all part of verification.

## User Experience — 15%

The console is designed as an operator sequence:

1. Reset a dedicated demo bank.
2. Run the next incident and view the grounded result.
3. Open a memory card to inspect the evidence and score.
4. Compare cold versus memory-assisted triage.
5. Use the manual intake and incident ledger to prove the system learns from new work.
6. Export a brief or create a reviewed handoff only after a human decision.

The UI reads demo status from the backend, so a page refresh or a completed sequence
does not silently issue an invalid extra step. A completed demo tells the user to reset.

## Real-world Impact — 10%

Sentinel targets the recurring operational failure mode where incident knowledge exists
in postmortems, tickets, and chat logs but is not available under pager pressure. A
production adoption path is incremental:

1. Start with a team-specific Hindsight bank and postmortem import.
2. Connect Azure Monitor or another alert source through the validated alert adapter.
3. Use Teams/GitHub handoffs for human review; do not automate production changes.
4. Measure time-to-mitigation, citation accuracy, and recurrence detection before
   expanding to runbook orchestration.

This design keeps the high-risk action outside the agent while preserving a full audit
trail from alert, to recalled evidence, to human-approved handoff.

## Judge checklist

- Open [LIVE_DEMO_PLAYBOOK.md](LIVE_DEMO_PLAYBOOK.md) and follow the 90-second flow.
- Confirm `/api/health` reports the intended providers.
- Show Memory Impact, cited IDs, and the Memory Inspector.
- Use an Azure schema payload and Teams/GitHub controls.
- Demonstrate that the runbook control requires human confirmation.
