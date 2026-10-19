import type {
  AuthResponse,
  LoginInput,
  RegisterInput,
  User,
} from "@/types/auth";

import { expireAccessToken, getAccessToken } from "@/services/auth-storage";

const API_BASE_URL = "";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchJson<T>(
  url: string,
  options: RequestInit,
  protectedRequest = false,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);

    if (protectedRequest && response.status === 401) expireAccessToken();

    const message = errorBody && typeof errorBody === "object" && "message" in errorBody
      ? String(errorBody.message)
      : errorBody && typeof errorBody === "object" && "detail" in errorBody
        ? typeof errorBody.detail === "string" ? errorBody.detail : JSON.stringify(errorBody.detail)
        : `Request failed with status ${response.status}`;
    const code = errorBody && typeof errorBody === "object" && "error" in errorBody
      ? String(errorBody.error)
      : undefined;

    throw new ApiError(message, response.status, code);
  }

  return response.json() as Promise<T>;
}

export interface LoginResult {
  access_token?: string;
  token_type?: string;
  requires_otp?: boolean;
  challenge_id?: string;
}

export async function login(data: LoginInput): Promise<LoginResult> {
  return fetchJson<LoginResult>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function register(
  data: RegisterInput
): Promise<User> {
  const payload = {
    email: data.email,
    password: data.password,
    name: data.name,
  };

  return fetchJson<User>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyEmail(data: { email: string; code: string }): Promise<{ message: string }> {
  return fetchJson("/api/auth/verify-email", { method: "POST", body: JSON.stringify(data) });
}

export async function resendVerification(email: string): Promise<{ message: string }> {
  return fetchJson("/api/auth/resend-verification", { method: "POST", body: JSON.stringify({ email }) });
}

export async function forgotPassword(email: string): Promise<{ message: string }> {
  return fetchJson("/api/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
}

export async function resetPassword(data: { email: string; code: string; new_password: string }): Promise<{ message: string }> {
  return fetchJson("/api/auth/reset-password", { method: "POST", body: JSON.stringify(data) });
}

export async function verifyLoginOtp(data: { challenge_id: string; code: string }): Promise<AuthResponse> {
  return fetchJson<AuthResponse>("/api/auth/login/verify-otp", { method: "POST", body: JSON.stringify(data) });
}

export async function getSecuritySettings(): Promise<{ email_verified: boolean; two_factor_enabled: boolean }> {
  return fetchJson("/api/auth/security", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
  }, true);
}

export async function requestTwoFactorCode(data: { current_password: string; action: "enable" | "disable" }): Promise<{ message: string }> {
  return fetchJson("/api/auth/2fa/send-code", {
    method: "POST",
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
    body: JSON.stringify(data),
  }, true);
}

export async function confirmTwoFactor(data: { current_password: string; code: string }, action: "enable" | "disable"): Promise<{ two_factor_enabled: boolean }> {
  return fetchJson(`/api/auth/2fa/${action}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
    body: JSON.stringify(data),
  }, true);
}

export async function getMe(): Promise<User> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return fetchJson<User>("/api/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }, true);
}

export async function logout(): Promise<void> {
  const token = getAccessToken();
  if (!token) return;
  const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    if (response.status === 401) expireAccessToken();
    throw new ApiError(`Logout failed with status ${response.status}.`, response.status);
  }
}
