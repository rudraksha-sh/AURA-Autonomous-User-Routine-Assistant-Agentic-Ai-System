const ACCESS_TOKEN_KEY = "aura_access_token";
const SESSION_EXPIRED_EVENT = "aura:session-expired";
const AUTH_CHANGED_EVENT = "aura:auth-changed";

function notifyAuthChanged() {
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function setAccessToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
  notifyAuthChanged();
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  notifyAuthChanged();
}

export function expireAccessToken(): void {
  clearAccessToken();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }
}
