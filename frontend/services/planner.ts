import { expireAccessToken, getAccessToken } from "@/services/auth-storage";
import type { Task } from "@/types/task";
import type { PlanPreview, ProposedPlanTask } from "@/types/planner";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class PlannerApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "PlannerApiError";
  }
}

async function request<T>(path: string, body: unknown): Promise<T> {
  const token = getAccessToken();
  if (!token) {
    expireAccessToken();
    throw new PlannerApiError("Authentication required.", 401);
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    });
  } catch {
    throw new PlannerApiError("Could not reach AURA. Check your connection and retry.", 0);
  }
  if (response.status === 401) expireAccessToken();
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload && typeof payload === "object" && "detail" in payload ? String(payload.detail) : `Request failed (${response.status}).`;
    throw new PlannerApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export function generatePlan(goalId: number): Promise<PlanPreview> {
  return request(`/api/planner/goals/${goalId}/plan`, { task_count: 5 });
}

export function savePlan(goalId: number, idempotencyKey: string, tasks: ProposedPlanTask[]): Promise<{ tasks: Task[] }> {
  return request(`/api/planner/goals/${goalId}/save`, { idempotency_key: idempotencyKey, tasks });
}
