import { expireAccessToken, getAccessToken } from "@/services/auth-storage";
import type { CreateTaskInput, Task, TaskActivity, TaskBulkActionResult, TaskSubtask, UpdateTaskInput } from "@/types/task";

const API_BASE_URL = "";

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

export const runBulkTaskAction = (taskIds: number[], action: "complete" | "delete") =>
  fetchJson<TaskBulkActionResult>("/api/tasks/bulk", { method: "POST", body: JSON.stringify({ task_ids: taskIds, action }) });

export const getTaskSubtasks = (taskId: number) =>
  fetchJson<TaskSubtask[]>(`/api/tasks/${taskId}/subtasks`);

export const createTaskSubtask = (taskId: number, title: string) =>
  fetchJson<TaskSubtask>(`/api/tasks/${taskId}/subtasks`, { method: "POST", body: JSON.stringify({ title }) });

export const updateTaskSubtask = (taskId: number, subtaskId: number, data: Partial<Pick<TaskSubtask, "title" | "is_completed" | "position">>) =>
  fetchJson<TaskSubtask>(`/api/tasks/${taskId}/subtasks/${subtaskId}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteTaskSubtask = (taskId: number, subtaskId: number) =>
  fetchJson<void>(`/api/tasks/${taskId}/subtasks/${subtaskId}`, { method: "DELETE" });

export const getTaskActivity = (taskId: number) =>
  fetchJson<TaskActivity[]>(`/api/tasks/${taskId}/activity`);
