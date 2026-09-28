# Hindsight Integration (the 25% criterion)

Hindsight is the memory layer. **The LLM never invents incident history — Hindsight is the source of truth.** The LLM only reasons over what Hindsight recalls.

Reference: <https://hindsight.vectorize.io/api-reference> · Retain guide: <https://docs.hindsight.vectorize.io/retain/>

## Core operations we use

| Op | Endpoint | When |
|----|----------|------|
| **retain** | `POST /v1/default/banks/{bank_id}/memories` | After an incident is resolved |
| **recall** | `POST /v1/default/banks/{bank_id}/memories/recall` | The moment a new alert fires |
| **reflect** | `POST /v1/default/banks/{bank_id}/reflect` | Optional: synthesized NL answer w/ evidence |
| **getMentalModel** | `GET /v1/default/banks/{bank_id}/mental-models` | The "genius moment" — pre-synthesized pattern summary |

Hindsight fact types: **`world`** (permanent truths), **`experience`** (things that happened), **`observation`** (auto-synthesized). Recall supports **tags**, **temporal windows**, and **spreading activation** over an entity knowledge graph.

---

## 1. Memory Write — `retain`

One `experience` memory per resolved incident. `content` is a **narrative** (best for fact extraction + semantic recall); `tags` are for deterministic filtering and occurrence counting.

`POST /v1/default/banks/acme-sre/memories`

```json
{
  "items": [
    {
      "content": "INCIDENT INC-1047 (RESOLVED). Service: checkout-service. Symptoms: p99 latency 3.2s, 5xx error rate 12%, onset 02:14 AM. Investigation: payments-service v2.3 deployed at 01:58 and leaked Redis connections; the checkout-service Redis connection pool saturated, causing checkout requests to block on Redis acquisition. Contributing factor: traffic overlapped the 02:00 nightly settlement batch. ROOT CAUSE: unbounded Redis connection pool in payments-service exhausting the shared pool. MITIGATION THAT WORKED: rolled back payments-service to v2.2 and restarted checkout-service to drain the pool; recovery in 8 min. PERMANENT FIX: bounded pool + connection timeout, tracked in JIRA-891 (NOT yet merged).",
      "context": "SRE production incident postmortem. Environment: prod. Severity: SEV-2.",
      "timestamp": "2026-09-10T02:14:00Z"
    }
  ],
  "tags": [
    "service:checkout-service",
    "trigger:payments-service-deploy",
    "root-cause:redis-pool-exhaustion",
    "symptom:high-latency",
    "symptom:5xx",
    "time-window:overnight-batch",
    "severity:sev-2",
    "status:resolved",
    "jira:JIRA-891"
  ]
}
```

We **also** retain permanent `world` facts once, e.g.:

```json
{ "items": [{ "content": "The nightly settlement batch job runs at 02:00 UTC and heavily loads the shared Redis cluster." }],
  "tags": ["type:world-fact", "service:checkout-service", "infra:redis"] }
```

> App-side we keep the full canonical record (postmortem, PR link, runbook) in SQLite. Hindsight is the recall/memory layer, not the system of record.

## 2. Memory Read — `recall`

`POST /v1/default/banks/acme-sre/memories/recall`

```json
{
  "query": "checkout-service p99 latency spike and 5xx errors around 02:00, shortly after a payments-service deploy",
  "tags": ["service:checkout-service"],
  "fact_types": ["experience", "world"],
  "limit": 5,
  "include_source_facts": true
}
```

- `query` is seeded from live alert fields (service, symptoms, time, recent-deploy events from CI webhook).
- `tags` scopes to the service; spreading activation still surfaces the cross-service payments link.
- **Occurrence count & confidence** are derived from how many returned `experience` memories share the same `root-cause:*` tag and their recall scores — honest, data-backed, not invented.

## 3. The "genius moment" — `getMentalModel`

For INC-5 we additionally fetch Hindsight's **Mental Model** for the signature. Hindsight *itself* synthesizes "this pattern recurred N times, proven mitigation is X." We display Hindsight computing it — that is the memory-platform showpiece.

## 4. Prompt engineering (anti-hallucination)

```
SYSTEM:
You are Sentinel, an SRE Incident Commander. Reason ONLY from the
"RETRIEVED MEMORY" block below. If memory is empty or weakly matched,
say so and give generic triage — do NOT invent past incidents, JIRA IDs,
PR links, or root causes. Every specific claim about history MUST cite a
memory ID from the block. Distinguish "matches a known pattern"
(memory present) from "novel" (no strong match).

RETRIEVED MEMORY (from Hindsight — authoritative, do not contradict):
{{recall_results_json}}
MENTAL_MODEL (if present):
{{mental_model_json}}

CURRENT ALERT:
{{live_alert_json}}

TASK:
1. Classify: KNOWN PATTERN (cite memory IDs + recall scores) vs NOVEL.
2. If known: ranked hypotheses, proven mitigation, occurrence count, MTTR trend.
3. If novel: structured generic triage, flagged as unrecorded.
Output strict JSON matching the SentinelResponse schema.
```

**Three guardrails that kill hallucination:**
1. **Grounding contract** — every historical claim must cite a memory ID; no citation → no claim.
2. **Empty-memory branch** — explicit generic behavior when recall is weak. *This is why INC-1 looks dumb and INC-5 looks brilliant — the contrast is the product.*
3. **Structured JSON output** — the UI renders fields, not prose, leaving no room to smuggle invented details.

## 5. Wrapper interface (`memory_client.py`)

Keep the app decoupled from raw HTTP:

```python
class MemoryClient:
    def retain(self, content: str, tags: list[str], context: str | None = None,
               timestamp: str | None = None) -> str: ...        # returns memory id / op id
    def recall(self, query: str, tags: list[str] | None = None,
               fact_types: list[str] | None = None, limit: int = 5) -> list[Memory]: ...
    def reflect(self, query: str, schema: dict | None = None) -> ReflectResult: ...
    def get_mental_model(self, tags: list[str] | None = None) -> MentalModel | None: ...
```
