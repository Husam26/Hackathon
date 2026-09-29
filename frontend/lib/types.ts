export type Classification = "KNOWN_PATTERN" | "NOVEL";
export type Severity = "SEV-1" | "SEV-2" | "SEV-3" | "SEV-4";

export interface MemoryPreferences {
  recency: "past_30_days" | "past_quarter" | "all_history";
  severities: Severity[];
}

export interface Health {
  status: "ok" | "degraded";
  version: string;
  providers: { memory: string; analysis: string };
}

export interface Alert {
  service: string;
  fired_at: string;
  severity: Severity;
  metrics: Record<string, number>;
  signals: string[];
  recent_deploys: { service: string; version: string; at: string }[];
}

export interface RecalledMemory {
  id: string;
  content: string;
  tags: string[];
  recall_score: number;
  timestamp: string | null;
  fact_type: "world" | "experience" | "observation" | null;
  retrieval_scores: Record<string, number>;
}

export interface Hypothesis {
  rank: number;
  description: string;
  confidence: number;
  based_on_memory_ids: string[];
}

export interface SentinelResponse {
  classification: Classification;
  summary: string;
  hypotheses: Hypothesis[];
  recommended_mitigation: string | null;
  occurrence_count: number;
  confidence: number;
  cited_memory_ids: string[];
  mttr_trend_minutes: number[];
  escalation: string | null;
}

export interface MemoryImpact {
  recalled_count: number;
  grounded_citation_count: number;
  highest_relevance: number | null;
  temporal_bias_applied: boolean;
  severity_tags_applied: string[];
}

export interface AnalysisResult {
  alert: Alert;
  response: SentinelResponse;
  recalled_memories: RecalledMemory[];
  memory_impact: MemoryImpact;
  mental_model: {
    id: string;
    name: string;
    content: string | null;
    tags: string[];
    is_stale: boolean;
    last_refreshed_at: string | null;
  } | null;
}

export interface ManualIncidentInput {
  title: string;
  service: string;
  severity: Severity;
  occurred_at?: string;
  signals: string[];
  root_cause: string;
  mitigation: string;
  mttr_minutes?: number;
}

export interface IncidentArtifacts {
  pr: string | null;
  runbook: string | null;
  jira: string | null;
}

export interface Incident {
  id: string;
  seq: number;
  title: string;
  mttr_minutes: number | null;
  alert: Alert;
  root_cause: string | null;
  mitigation: string | null;
  retained_memory_id: string | null;
  artifacts: IncidentArtifacts;
}

export interface IncidentAnalysisRun {
  source: "manual" | "historical";
  incident: Incident;
  analysis: AnalysisResult;
}

export interface ArtifactLink {
  label: string;
  url: string;
  kind: "github_issue" | "pull_request" | "runbook" | "issue_search";
}

export interface DemoStatus {
  position: number;
  total_steps: number;
  next_incident_id: string | null;
}

export interface DemoStep {
  step: number;
  total_steps: number;
  incident: Incident;
  analysis: AnalysisResult;
}