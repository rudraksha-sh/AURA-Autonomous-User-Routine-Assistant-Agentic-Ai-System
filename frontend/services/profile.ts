import { ApiError } from "@/services/auth";
import { expireAccessToken, getAccessToken, setAccessToken } from "@/services/auth-storage";

const API_BASE_URL = "";

export interface Profile {
  id: number;
  name: string;
  email: string;
  role: "user" | "admin";
  profile_photo_available: boolean;
}

export type ThemePreference = "light" | "dark" | "system";
export type AppearancePreferences = {
  theme: ThemePreference;
  accent_color: "blue" | "violet" | "emerald" | "rose" | "amber";
  density: "comfortable" | "compact";
  font_size: "small" | "medium" | "large";
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) throw new ApiError("Authentication required.", 401);
  const response = await fetch(`${API_BASE_URL}/api/profile${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, ...init.headers },
  });
  if (!response.ok) {
    if (response.status === 401) expireAccessToken();
    const body = await response.json().catch(() => null);
    throw new ApiError(typeof body?.detail === "string" ? body.detail : `Request failed (${response.status}).`, response.status);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

export function fetchProfile() { return request<Profile>(""); }
export function fetchThemePreference() { return request<{ theme: ThemePreference }>("/theme"); }
export function fetchAppearancePreferences() { return request<AppearancePreferences>("/appearance"); }
export function saveAppearancePreferences(data: AppearancePreferences) {
  return request<AppearancePreferences & { access_token: string }>("/appearance", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }).then((result) => {
    setAccessToken(result.access_token);
    return { theme: result.theme, accent_color: result.accent_color, density: result.density, font_size: result.font_size };
  });
}
export async function changePassword(data: { current_password: string; new_password: string }) {
  const result = await request<{ access_token: string }>("/password", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
  setAccessToken(result.access_token);
}
export function saveProfile(data: Pick<Profile, "name" | "email">) {
  return requestMutation("", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
}
export function uploadProfilePhoto(file: File) {
  const form = new FormData();
  form.append("file", file);
  return requestMutation("/photo", { method: "POST", body: form });
}
export function removeProfilePhoto() { return requestMutation("/photo", { method: "DELETE" }); }

export async function saveThemePreference(theme: ThemePreference): Promise<ThemePreference> {
  const result = await request<{ theme: ThemePreference; access_token: string }>("/theme", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme }),
  });
  setAccessToken(result.access_token);
  return result.theme;
}

async function requestMutation(path: string, init: RequestInit): Promise<Profile> {
  const result = await request<Profile & { access_token: string }>(path, init);
  setAccessToken(result.access_token);
  return {
    id: result.id,
    name: result.name,
    email: result.email,
    role: result.role,
    profile_photo_available: result.profile_photo_available,
  };
}

export async function fetchProfilePhoto(): Promise<string | null> {
  const token = getAccessToken();
  if (!token) return null;
  const response = await fetch(`${API_BASE_URL}/api/profile/photo`, { headers: { Authorization: `Bearer ${token}` } });
  if (response.status === 404) return null;
  if (response.status === 401) { expireAccessToken(); return null; }
  if (!response.ok) throw new ApiError(`Photo request failed (${response.status}).`, response.status);
  return URL.createObjectURL(await response.blob());
}
