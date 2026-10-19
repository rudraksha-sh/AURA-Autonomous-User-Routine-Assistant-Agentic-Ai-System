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
    public readonly status: number
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

    const message =
      errorBody && typeof errorBody === "object" && "message" in errorBody
        ? String(errorBody.message)
        : errorBody && typeof errorBody === "object" && "detail" in errorBody
          ? JSON.stringify(errorBody.detail)
          : `Request failed with status ${response.status}`;

    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

export async function login(
  data: LoginInput
): Promise<AuthResponse> {
  return fetchJson<AuthResponse>("/api/auth/login", {
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
