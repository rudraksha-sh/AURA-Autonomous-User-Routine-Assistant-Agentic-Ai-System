import type {
  AuthResponse,
  LoginInput,
  RegisterInput,
  User,
} from "@/types/auth";

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

    const message =
      errorBody &&
      typeof errorBody === "object" &&
      "message" in errorBody
        ? String(errorBody.message)
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
  return fetchJson<User>("/api/auth/me", {
    method: "GET",
  });
}