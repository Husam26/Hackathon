# Sentinel Workflow Diagrams

These Mermaid diagrams are the reviewer-readable counterpart to the API endpoint:

```text
GET /api/architecture/workflow
```

The endpoint is the runtime source for tools; this document is the stable, rendered
review reference.

## End-to-end operator sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as On-Call SRE / Demo
    participant Console as Next.js Console (Demo / Manual)
    participant API as FastAPI HTTP Routes
    participant Orch as Sentinel Orchestrator
    participant Mem as Hindsight / Local Mirror
    participant LLM as Groq / Gemini / Rules
    participant DB as SQLite DB
    participant Ext as Teams / GitHub Handoff

    User->>Console: Select /demo or /manual workspace
    alt Guided demo
        Console->>API: POST /api/demo/step + retrieval preferences
    else Manual intake or historical record
        Console->>API: POST /api/incidents/manual/analyze
        Note over Console,API: Or POST /api/incidents/{id}/analyze
    else Azure Monitor intake
        Console->>API: POST /api/integrations/azure-monitor
    end
    API->>Orch: Validate strict Pydantic contract

    rect rgb(230, 245, 255)
        Note right of Orch: Phase 1: Context retrieval and operator bias
        Orch->>Mem: Recall service, symptoms, deploys, temporal window, severity tags
        Mem-->>Orch: Matching incidents, scores, tags
        alt At least two relevant memories
            Orch->>Mem: Fetch consolidated mental model
            Mem-->>Orch: Recurring-pattern context
        end
    end

    rect rgb(240, 255, 240)
        Note right of Orch: Phase 2: Grounded reasoning and validation
        Orch->>LLM: Alert + recalled evidence + allowed citation IDs
        LLM-->>Orch: Structured classification, hypotheses, mitigation
        Orch->>Orch: Validate JSON and citation allow-list
        alt Provider or contract failure
            Orch->>LLM: Groq -> Gemini -> grounded rules fallback
        end
    end

    Orch-->>API: AnalysisResult + Memory Impact + evidence
    API-->>Console: Live command thread, Hindsight inspector, MTTR, controls

    rect rgb(255, 245, 230)
        Note right of Orch: Phase 3: Retention and safe enterprise handoff
        User->>Console: Analyze & save manual incident / complete demo
        Console->>API: POST /api/incidents/manual/analyze or /api/incidents
        Orch->>Mem: Retain resolution narrative and local mirror
        Orch->>DB: Upsert canonical incident record and artifacts
        User->>Console: Teams export, GitHub Issue, runbook verification
        Console->>Ext: Prepare human-reviewed handoff only
    end
```

## System architecture

```mermaid
flowchart TD
    subgraph Frontend["Frontend: Next.js 16 Console"]
        NAV["Navigation: /demo and /manual"]
        DEMO["Guided Demo: five-step learning curve"]
        MANUAL["Manual Intake + Incident Ledger"]
        UI["Command Thread, Memory Inspector, MTTR, Handoffs"]
        NAV --> DEMO
        NAV --> MANUAL
        DEMO --> UI
        MANUAL --> UI
    end

    subgraph Delivery["FastAPI delivery: backend/http/routes"]
        SYSTEM["System + workflow-diagram endpoint"]
        ANALYSIS["Analysis, Azure, Teams, GitHub, Runbook"]
        INCIDENTS["Manual, historical replay, artifact navigation"]
        DEMOROUTES["Demo status, step, reset"]
        SOCKET["WebSocket analysis"]
    end

    subgraph Application["Application layer"]
        SCHEMAS["Strict Pydantic validation"]
        ORCH["SentinelOrchestrator"]
        PREFS["Recency window + severity tag bias"]
        RUNS["IncidentAnalysisRun contract"]
    end

    subgraph Intelligence["Memory, reasoning, and records"]
        MEM["Hindsight Cloud + local mirrored fallback"]
        MENTAL["Mental model retrieval"]
        LLM["Groq -> Gemini -> grounded rules"]
        DB[("SQLite canonical store")]
        EXT["Teams brief / GitHub Issue / approval-gated runbook"]
    end

    UI <-->|REST / WebSocket| SYSTEM
    UI <-->|REST| ANALYSIS
    UI <-->|REST| INCIDENTS
    UI <-->|REST| DEMOROUTES
    UI <-->|WebSocket| SOCKET
    SYSTEM --> SCHEMAS
    ANALYSIS --> SCHEMAS
    INCIDENTS --> RUNS
    DEMOROUTES --> ORCH
    SCHEMAS --> ORCH
    PREFS --> ORCH
    RUNS --> ORCH
    ORCH <-->|Recall evidence| MEM
    ORCH <-->|Fetch recurring pattern| MENTAL
    ORCH <-->|Grounded reasoning| LLM
    ORCH <-->|Retain and upsert| DB
    ANALYSIS --> EXT
    INCIDENTS --> EXT
    ORCH -->|AnalysisResult + evidence| UI
```

## Design boundaries

- Hindsight retrieves and ranks memory; it is not replaced by UI filters.
- The analyzer may cite only IDs returned by current recall.
- Manual analysis happens before the newly submitted record is retained, avoiding
  self-citation.
- SQLite is the canonical record; Hindsight is the semantic recall layer.
- External controls prepare a reviewed handoff. They do not execute production
  commands, create GitHub issues, or post to Teams automatically.
