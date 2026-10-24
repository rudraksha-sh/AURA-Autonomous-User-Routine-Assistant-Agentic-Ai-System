import { expireAccessToken, getAccessToken } from "@/services/auth-storage";
import type {
  CreateGoalInput,
  Goal,
  UpdateGoalInput,
} from "@/types/goal";

const API_BASE_URL = "";

export class GoalApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "GoalApiError";
  }
}

async function fetchJson<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();

  if (!token) {
    expireAccessToken();
    throw new GoalApiError("Authentication required.", 401);
  }

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...options.headers,
      },
    });
  } catch {
    throw new GoalApiError(
      "Could not reach AURA. Check your connection and retry.",
      0
    );
  }

  if (!response.ok) {
    if (response.status === 401) {
      expireAccessToken();
    }

    const body = await response.json().catch(() => null);
    const message =
      body &&
      typeof body === "object" &&
      "detail" in body
        ? String(body.detail)
        : `Request failed with status ${response.status}.`;

    throw new GoalApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const getGoals = () =>
  fetchJson<Goal[]>("/api/goals");

export const getGoal = (goalId: number) =>
  fetchJson<Goal>(`/api/goals/${goalId}`);

export const createGoal = (data: CreateGoalInput) =>
  fetchJson<Goal>("/api/goals", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateGoal = (
  goalId: number,
  data: UpdateGoalInput
) =>
  fetchJson<Goal>(`/api/goals/${goalId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteGoal = (goalId: number) =>
  fetchJson<void>(`/api/goals/${goalId}`, {
    method: "DELETE",
  });
