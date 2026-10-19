import { expireAccessToken, getAccessToken } from "@/services/auth-storage";

export type NotificationPreferences = {
  due_soon_reminders: boolean;
  overdue_alerts: boolean;
  weekly_summary: boolean;
  reminder_lead_time_minutes: 15 | 30 | 60 | 1440;
};

async function request<T>(init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) { expireAccessToken(); throw new Error("Authentication required."); }
  const response = await fetch("/api/notifications/preferences", {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init.headers },
  });
  if (response.status === 401) expireAccessToken();
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export function getNotificationPreferences() { return request<NotificationPreferences>(); }
export function saveNotificationPreferences(data: NotificationPreferences) {
  return request<NotificationPreferences>({ method: "PUT", body: JSON.stringify(data) });
}
