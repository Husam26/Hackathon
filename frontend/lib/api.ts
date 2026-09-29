import type { AnalysisResult, Alert, DemoStatus, DemoStep, Health, Incident, ManualIncidentInput, MemoryPreferences } from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(body: unknown, status: number): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg ?? "Invalid request").join("; ");
    }
  }
  return `Request failed (${status})`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(
      0,
      `Unable to reach Sentinel API at ${API_URL}. Check that the backend is running.`,
    );
  }

  if (response.status === 204) return undefined as T;
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      throw new ApiError(response.status, "Sentinel API returned invalid JSON.");
    }
  }
  if (!response.ok) throw new ApiError(response.status, errorMessage(body, response.status));
  if (body === null) throw new ApiError(response.status, "Sentinel API returned an empty response.");
  return body as T;
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
