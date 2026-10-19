import { expireAccessToken, getAccessToken, setAccessToken } from "@/services/auth-storage";

export type AIProviderStatus = { provider: "openrouter" | "deterministic"; configured: boolean; fallback_available: boolean };
export type AIPlanningPreference = { use_ai_planning: boolean };

async function request<T>(url: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) { expireAccessToken(); throw new Error("Authentication required."); }
  const response = await fetch(url, { ...init, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init.headers } });
  if (response.status === 401) expireAccessToken();
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export const getAIProviderStatus = () => request<AIProviderStatus>("/api/ai/status");
export const getAIPlanningPreference = () => request<AIPlanningPreference>("/api/profile/ai-planning");
export async function saveAIPlanningPreference(use_ai_planning: boolean) {
  const result = await request<AIPlanningPreference & { access_token: string }>("/api/profile/ai-planning", { method: "PUT", body: JSON.stringify({ use_ai_planning }) });
  setAccessToken(result.access_token);
  return { use_ai_planning: result.use_ai_planning };
}
