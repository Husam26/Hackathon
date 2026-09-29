"""Mermaid diagrams describing Sentinel's complete operator workflow."""

from pydantic import BaseModel


class WorkflowDiagrams(BaseModel):
    sequence_diagram: str
    architecture_flowchart: str


def workflow_diagrams() -> WorkflowDiagrams:
    return WorkflowDiagrams(
        sequence_diagram="""sequenceDiagram
    autonumber
    actor User as On-Call SRE / Demo
    participant Console as Next.js Console (Demo / Manual)
    participant API as FastAPI HTTP Routes
    participant Orch as Sentinel Orchestrator
    participant Mem as Hindsight / Local Mirror
    participant LLM as Groq -> Gemini -> Rules
    participant DB as SQLite Canonical Store
    participant Ext as Teams / GitHub Handoff

    User->>Console: Select Demo or Manual workspace
    alt Guided demo
        Console->>API: POST /api/demo/step + retrieval preferences
    else Manual intake or prior incident
        Console->>API: POST /api/incidents/manual/analyze\nOR POST /api/incidents/{id}/analyze
    else Azure Monitor alert
        Console->>API: POST /api/integrations/azure-monitor
    end
    API->>Orch: Validate strict Pydantic contract and start analysis

    rect rgb(230, 245, 255)
    note right of Orch: Phase 1: Context retrieval and operator bias
    Orch->>Mem: Recall by service, symptoms, deploys, temporal window, severity tags
    Mem-->>Orch: Recalled incidents, scores, and tags
    alt Two or more relevant memories
        Orch->>Mem: Fetch consolidated mental model
        Mem-->>Orch: Recurring-pattern context
    end
    end

    rect rgb(240, 255, 240)
    note right of Orch: Phase 2: Grounded reasoning and fallback
    Orch->>LLM: Alert + recalled evidence + allowed citation IDs
    LLM-->>Orch: Structured classification, hypotheses, mitigation
    Orch->>Orch: Validate JSON and citation allow-list
    alt Provider failure
        Orch->>LLM: Fail over Groq -> Gemini -> grounded rules
    end
    end

    Orch-->>API: AnalysisResult + Memory Impact + evidence
    API-->>Console: Live command thread, Hindsight inspector, MTTR, controls

    rect rgb(255, 245, 230)
    note right of Orch: Phase 3: Resolution, retention, and safe handoff
    User->>Console: Analyze & save manual incident / complete demo
    Console->>API: POST /api/incidents/manual/analyze or /api/incidents
    Orch->>Mem: Retain resolved narrative; mirror locally on success
    Orch->>DB: Upsert canonical incident and artifact references
    User->>Console: Export Teams, open GitHub Issue, verify runbook
    Console->>Ext: Prepare human-reviewed handoff only
    end""",
        architecture_flowchart="""flowchart TD
    subgraph Frontend["Frontend: Next.js 16 Console"]
        NAV["Workspace navigation: /demo and /manual"]
        DEMO["Guided Demo: learning curve + MTTR"]
        MANUAL["Manual Intake + Incident Ledger"]
        UI["Command Thread, Memory Inspector, Controls, Handoffs"]
        NAV --> DEMO
        NAV --> MANUAL
        DEMO --> UI
        MANUAL --> UI
    end

    subgraph Delivery["FastAPI Delivery Layer: backend/http/routes"]
        SYSTEM["System + architecture workflow endpoint"]
        ANALYSIS["Analysis, Azure Monitor, Teams, GitHub, Runbook routes"]
        INCIDENTS["Manual, historical replay, artifact routes"]
        DEMOROUTES["Demo status, step, reset routes"]
        SOCKET["WebSocket analysis route"]
    end

    subgraph Application["Application Layer"]
        SCHEMAS["Strict Pydantic contracts"]
        ORCH["SentinelOrchestrator"]
        PREFS["Recency window + severity-tag preferences"]
        RUNS["IncidentAnalysisRun contracts"]
    end

    subgraph Intelligence["Memory, Reasoning, and Record Layer"]
        MEM["Hindsight Cloud with local mirrored fallback"]
        MENTAL["Mental model retrieval"]
        LLM["Groq primary -> Gemini -> grounded rules"]
        DB[("SQLite canonical incident store")]
        EXT["Teams-ready brief / pre-filled GitHub Issue / approval-gated runbook"]
    end

    UI <-->|"REST / WebSocket"| SYSTEM
    UI <-->|"REST"| ANALYSIS
    UI <-->|"REST"| INCIDENTS
    UI <-->|"REST"| DEMOROUTES
    UI <-->|"WebSocket"| SOCKET
    SYSTEM --> SCHEMAS
    ANALYSIS --> SCHEMAS
    INCIDENTS --> RUNS
    DEMOROUTES --> ORCH
    SCHEMAS --> ORCH
    PREFS --> ORCH
    RUNS --> ORCH
    ORCH <-->|"1. recall evidence"| MEM
    ORCH <-->|"2. retrieve pattern"| MENTAL
    ORCH <-->|"3. grounded reasoning"| LLM
    ORCH <-->|"4. retain + upsert"| DB
    ANALYSIS --> EXT
    INCIDENTS --> EXT
    ORCH -->|"AnalysisResult + evidence"| UI""",
    )
