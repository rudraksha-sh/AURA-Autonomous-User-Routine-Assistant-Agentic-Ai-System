import { expireAccessToken, getAccessToken } from "@/services/auth-storage";
import { ApiError } from "@/services/auth";
import type {
  CreateGoalInput,
  Goal,
  UpdateGoalInput,
} from "@/types/goal";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchJson<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();

  if (!token) {
    expireAccessToken();
    throw new ApiError("Authentication required.", 401);
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401) expireAccessToken();
    const errorBody = await response.json().catch(() => null);

    const message =
      errorBody &&
      typeof errorBody === "object" &&
      "detail" in errorBody
        ? JSON.stringify(errorBody.detail)
        : `Request failed with status ${response.status}`;

    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function getGoals(): Promise<Goal[]> {
  return fetchJson<Goal[]>("/api/goals", {
    method: "GET",
  });
}

export async function getGoal(goalId: number): Promise<Goal> {
  return fetchJson<Goal>(`/api/goals/${goalId}`, {
    method: "GET",
  });
}

export async function createGoal(
  data: CreateGoalInput
): Promise<Goal> {
  return fetchJson<Goal>("/api/goals", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateGoal(
  goalId: number,
  data: UpdateGoalInput
): Promise<Goal> {
  return fetchJson<Goal>(`/api/goals/${goalId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteGoal(goalId: number): Promise<void> {
  return fetchJson<void>(`/api/goals/${goalId}`, {
    method: "DELETE",
  });
}
