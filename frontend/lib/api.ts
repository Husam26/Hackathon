import type { AnalysisResult, Alert, DemoStatus, DemoStep, Health, Incident, ManualIncidentInput, MemoryPreferences } from "@/lib/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const sentinelApi = {
  health: () => request<Health>("/api/health"),
  demoStatus: () => request<DemoStatus>("/api/demo/status"),
  step: (preferences?: MemoryPreferences) => request<DemoStep>("/api/demo/step", { method: "POST", body: preferences ? JSON.stringify(preferences) : undefined }),
  coldAnalysis: (alert: Alert) => request<AnalysisResult>("/api/analyze/cold", { method: "POST", body: JSON.stringify(alert) }),
  azureMonitor: (payload: Record<string, unknown>) => request<AnalysisResult>("/api/integrations/azure-monitor", { method: "POST", body: JSON.stringify(payload) }),
  githubHotfix: (incidentId: string) => request<{ label: string; url: string }>(`/api/integrations/github-hotfix/${incidentId}`),
  teamsExport: (incidentId: string, analysis: AnalysisResult) => request<{ markdown: string }>(`/api/integrations/teams-export/${incidentId}`, { method: "POST", body: JSON.stringify(analysis) }),
  verifyRunbook: (payload: { incident_id: string; action: "rollback_payments" | "restart_checkout"; confirmed_by_human: boolean }) => request<{ status: string; message: string; audit_note: string }>("/api/runbooks/verify", { method: "POST", body: JSON.stringify(payload) }),
  reset: () => request<void>("/api/demo/reset", { method: "POST" }),
  incidents: () => request<Incident[]>("/api/incidents"),
  createManualIncident: (payload: ManualIncidentInput) =>
    request<Incident>("/api/incidents/manual", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
