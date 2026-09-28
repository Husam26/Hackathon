export type Classification = "KNOWN_PATTERN" | "NOVEL";

export interface Health {
  status: "ok" | "degraded";
  version: string;
  providers: { memory: string; analysis: string };
}

export interface Alert {
  service: string;
  fired_at: string;
  severity: string;
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

export interface AnalysisResult {
  alert: Alert;
  response: SentinelResponse;
  recalled_memories: RecalledMemory[];
  mental_model: {
    id: string;
    name: string;
    content: string | null;
    tags: string[];
    is_stale: boolean;
    last_refreshed_at: string | null;
  } | null;
}

export interface Incident {
  id: string;
  seq: number;
  title: string;
  mttr_minutes: number | null;
  alert: Alert;
  root_cause: string | null;
}

export interface DemoStep {
  step: number;
  total_steps: number;
  incident: Incident;
  analysis: AnalysisResult;
}
