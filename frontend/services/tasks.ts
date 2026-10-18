import { expireAccessToken, getAccessToken } from "@/services/auth-storage";
import type { CreateTaskInput, Task, UpdateTaskInput } from "@/types/task";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class TaskApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "TaskApiError";
  }
}

async function fetchJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) {
    expireAccessToken();
    throw new TaskApiError("Authentication required.", 401);
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
    throw new TaskApiError("Could not reach AURA. Check your connection and retry.", 0);
  }

  if (!response.ok) {
    if (response.status === 401) expireAccessToken();
    const body = await response.json().catch(() => null);
    const message = body && typeof body === "object" && "detail" in body
      ? String(body.detail)
      : `Request failed with status ${response.status}.`;
    throw new TaskApiError(message, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const getTasks = () => fetchJson<Task[]>("/api/tasks");
export const createTask = (goalId: number, data: CreateTaskInput) =>
  fetchJson<Task>(`/api/tasks/goals/${goalId}/tasks`, { method: "POST", body: JSON.stringify(data) });
export const updateTask = (taskId: number, data: UpdateTaskInput) =>
  fetchJson<Task>(`/api/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(data) });
export const deleteTask = (taskId: number) =>
  fetchJson<void>(`/api/tasks/${taskId}`, { method: "DELETE" });
