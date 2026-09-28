# Data Model

## 1. `data/incidents.json` (the synthetic corpus)

The demo corpus: the 5 scripted incidents + 1–2 distractors. Each entry has an **alert** (what fires), an **investigation timeline**, the **resolution**, and the **retain payload** (what we store in Hindsight). Hyper-realistic — no foo/bar.

```jsonc
{
  "company": "Northwind Pay",
  "bank_id": "acme-sre",
  "incidents": [
    {
      "id": "INC-1047",
      "seq": 1,                          // demo order
      "is_recurring_spine": true,        // part of the Redis pattern
      "alert": {
        "service": "checkout-service",
        "fired_at": "2026-09-10T02:14:00Z",
        "severity": "SEV-2",
        "metrics": { "p99_latency_ms": 3200, "error_rate_5xx": 0.12, "rps": 4200 },
        "signals": ["p99 latency 3.2s", "5xx rate 12%", "Redis pool wait time rising"],
        "recent_deploys": [
          { "service": "payments-service", "version": "v2.3", "at": "2026-09-10T01:58:00Z" }
        ]
      },
      "timeline": [
        { "at": "02:14", "event": "PagerDuty alert: checkout-service SEV-2" },
        { "at": "02:31", "event": "Engineer notes payments-service v2.3 deployed 01:58" },
        { "at": "02:49", "event": "Redis connection pool saturation confirmed" },
        { "at": "03:20", "event": "Rolled back payments to v2.2; restarted checkout" },
        { "at": "03:44", "event": "Recovered. Filed JIRA-891 (bounded pool)." }
      ],
      "root_cause": "Unbounded Redis connection pool in payments-service exhausted the shared checkout pool.",
      "contributing_factors": ["Traffic overlapped 02:00 nightly settlement batch"],
      "mitigation": "Rolled back payments-service to v2.2 and restarted checkout-service to drain the pool.",
      "permanent_fix": { "status": "open", "ref": "JIRA-891", "desc": "Add bounded pool + connection timeout" },
      "mttr_minutes": 90,
      "artifacts": { "pr": null, "runbook": "runbooks/redis-pool.md", "jira": "JIRA-891" },
      "retain": {
        "content": "INCIDENT INC-1047 (RESOLVED). Service: checkout-service. Symptoms: p99 latency 3.2s, 5xx 12%, onset 02:14. payments-service v2.3 deployed 01:58 leaked Redis connections; checkout Redis pool saturated. Overlapped 02:00 settlement batch. ROOT CAUSE: unbounded Redis connection pool in payments-service. MITIGATION: rollback payments to v2.2 + restart checkout (8 min recovery). PERMANENT FIX: JIRA-891 (not merged).",
        "context": "SRE production incident postmortem. Environment: prod. Severity: SEV-2.",
        "timestamp": "2026-09-10T02:14:00Z",
        "tags": [
          "service:checkout-service", "trigger:payments-service-deploy",
          "root-cause:redis-pool-exhaustion", "symptom:high-latency", "symptom:5xx",
          "time-window:overnight-batch", "severity:sev-2", "status:resolved", "jira:JIRA-891"
        ]
      }
    }
    // INC-2 (orders-service Postgres lock — decoy)
    // INC-3 (checkout DB read-replica lag — ambiguous)
    // INC-4 (checkout Redis pool, payments v2.4 — 2nd spine hit)
    // INC-5 (checkout Redis pool, payments v2.5 — genius moment)
  ],
  "world_facts": [
    { "content": "The nightly settlement batch runs at 02:00 UTC and heavily loads the shared Redis cluster.",
      "tags": ["type:world-fact", "service:checkout-service", "infra:redis"] }
  ]
}
```

### Tag taxonomy (keep consistent — recall depends on it)
| Prefix | Example | Purpose |
|--------|---------|---------|
| `service:` | `service:checkout-service` | Scope recall to the affected service |
| `trigger:` | `trigger:payments-service-deploy` | Causal trigger |
| `root-cause:` | `root-cause:redis-pool-exhaustion` | **Occurrence counting** for pattern detection |
| `symptom:` | `symptom:high-latency` | Signature matching |
| `time-window:` | `time-window:overnight-batch` | Temporal correlation |
| `severity:` | `severity:sev-2` | Prioritization |
| `status:` | `status:resolved` | Filter resolved vs open |
| `jira:` / `type:` | `jira:JIRA-891`, `type:world-fact` | Cross-refs / fact typing |

## 2. Pydantic schemas (`backend/schemas.py`)

```python
class RecentDeploy(BaseModel):
    service: str; version: str; at: datetime

class Alert(BaseModel):
    service: str; fired_at: datetime; severity: str
    metrics: dict[str, float]; signals: list[str]
    recent_deploys: list[RecentDeploy] = []

class RecalledMemory(BaseModel):
    id: str; content: str; tags: list[str]
    recall_score: float; timestamp: datetime | None = None

class Hypothesis(BaseModel):
    rank: int; description: str; confidence: float
    based_on_memory_ids: list[str]           # grounding: must cite

class SentinelResponse(BaseModel):
    classification: Literal["KNOWN_PATTERN", "NOVEL"]
    summary: str
    hypotheses: list[Hypothesis]
    recommended_mitigation: str | None
    occurrence_count: int                     # from root-cause tag matches
    confidence: float
    cited_memory_ids: list[str]               # every historical claim cites one
    mttr_trend_minutes: list[int] = []        # e.g. [90, 15, 3]
    escalation: str | None = None             # e.g. "JIRA-891 open 6 weeks"

class IncidentRecord(BaseModel):              # SQLite system-of-record
    id: str; alert: Alert; root_cause: str | None
    mitigation: str | None; permanent_fix: dict | None
    mttr_minutes: int | None; artifacts: dict; retained_memory_id: str | None
```

## 3. Where each store lives
- **Hindsight** = recall/memory layer (narratives + tags, fact extraction, mental models).
- **SQLite** = system of record (full postmortems, PR links, runbooks, MTTR history for the chart).
