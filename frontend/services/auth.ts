import type {
  AuthResponse,
  LoginInput,
  RegisterInput,
  User,
} from "@/types/auth";

import { getAccessToken } from "@/services/auth-storage";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchJson<T>(
  url: string,
  options: RequestInit
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

    console.error("API error:", errorBody);

    const message =
      errorBody &&
      typeof errorBody === "object" &&
      "detail" in errorBody
        ? JSON.stringify(errorBody.detail)
        : `Request failed with status ${response.status}`;

    throw new Error(message);
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
): Promise<AuthResponse> {
  const payload = {
    email: data.email,
    password: data.password,
    name: data.name,
  };

  return fetchJson<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMe(): Promise<User> {
  const token = getAccessToken();

  if (!token) {
    throw new Error("Authentication required.");
  }

  return fetchJson<User>("/api/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}