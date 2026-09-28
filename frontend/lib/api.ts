import type { DemoStatus, DemoStep, Health } from "@/lib/types";

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
  step: () => request<DemoStep>("/api/demo/step", { method: "POST" }),
  reset: () => request<void>("/api/demo/reset", { method: "POST" }),
};
