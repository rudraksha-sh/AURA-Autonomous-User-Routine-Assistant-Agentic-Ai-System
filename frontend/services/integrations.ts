import { expireAccessToken, getAccessToken } from "@/services/auth-storage";

export type GoogleIntegrationStatus = {
  status: "connected" | "disconnected";
  scopes: string[];
  last_sync_at: string | null;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) { expireAccessToken(); throw new Error("Authentication required."); }
  const response = await fetch(`/api/integrations${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, ...init.headers },
  });
  if (response.status === 401) expireAccessToken();
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `Request failed (${response.status}).`);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

export function getGoogleIntegrationStatus() { return request<GoogleIntegrationStatus>("/google/status"); }
export type GoogleService = "calendar" | "gmail" | "drive" | "all";
export function disconnectGoogleIntegration(revoke = false) {
  return request<void>(revoke ? "/google?revoke_provider=true" : "/google", { method: "DELETE" });
}
export function getGoogleConnectUrl(service: GoogleService = "calendar") {
  const query = service === "all" ? "" : `?service=${service}`;
  return request<{ authorization_url: string }>(`/google/connect${query}`);
}
