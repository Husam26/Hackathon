# Data Model

## Corpus

`data/incidents.json` is validated as an `IncidentCorpus` before use. It contains:

- company and default bank metadata;
- five ordered demo incidents;
- two distractor incidents for retrieval realism;
- permanent world facts for the settlement window and unresolved fix.

Every incident contains a live alert, investigation timeline, root cause, contributing factors, mitigation, permanent-fix state, MTTR, artifacts, and the exact narrative/tags sent to memory.

## Core contracts

| Model | Key fields |
|---|---|
| `Alert` | service, UTC timestamp, severity, numeric metrics, signals, recent deploys |
| `IncidentRecord` | stable ID, sequence, alert, timeline, outcome, MTTR, artifacts, retain payload |
| `RecalledMemory` | fact/document ID, text, tags, relative score, fact type, timestamp |
| `MentalModel` | stable ID, name, content, tags, staleness, refresh timestamp |
| `SentinelResponse` | classification, hypotheses, mitigation, occurrence count, confidence, citations, MTTR trend, escalation |
| `AnalysisResult` | alert, response, recalled evidence, optional mental model |

Pydantic rejects unknown fields. Confidence and recall scores are constrained to `[0, 1]`, MTTR cannot be negative, severities are enumerated, incident IDs follow `INC-<number>`, and duplicate incident IDs, sequences, or tags are rejected.

## Tag taxonomy

| Prefix | Example | Use |
|---|---|---|
| `service:` | `service:checkout-service` | Recall scope |
| `trigger:` | `trigger:payments-service-deploy` | Causal trigger |
| `root-cause:` | `root-cause:redis-pool-exhaustion` | Pattern grouping and occurrence counting |
| `symptom:` | `symptom:high-latency` | Signature comparison |
| `time-window:` | `time-window:overnight-batch` | Temporal discrimination |
| `severity:` | `severity:sev-2` | Priority context |
| `status:` | `status:resolved` | Lifecycle state |
| `jira:` | `jira:JIRA-891` | External reference |
| `type:` | `type:world-fact` | Durable fact marker |

Tag consistency is functional, not cosmetic: service tags scope recall, signature tags discriminate similar alerts, and root-cause tags drive grounded occurrence counts.

## Persistence

Hindsight stores extracted and consolidated recall facts. SQLite stores a JSON snapshot of the validated canonical incident alongside indexed ID, sequence, service, status, MTTR, retained-memory ID, and update timestamp.

The SQLite upsert writes the memory operation/document identifier back into the stored incident snapshot so the canonical record can be traced to the recall layer.
