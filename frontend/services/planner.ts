import { expireAccessToken, getAccessToken } from "@/services/auth-storage";
import type { Task } from "@/types/task";
import type { DailySchedule, PlanPreview, PlanningPreferences, ProposedPlanTask, ScheduleEntryProposal, SchedulePreview, WhatIfRequest, WhatIfResult } from "@/types/planner";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class PlannerApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "PlannerApiError";
  }
}

async function request<T>(path: string, body?: unknown, method = "POST"): Promise<T> {
  const token = getAccessToken();
  if (!token) {
    expireAccessToken();
    throw new PlannerApiError("Authentication required.", 401);
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
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

export function getPlanningPreferences(): Promise<PlanningPreferences> {
  return request("/api/planner/preferences", undefined, "GET");
}

export function savePlanningPreferences(preferences: PlanningPreferences): Promise<PlanningPreferences> {
  return request("/api/planner/preferences", preferences, "PUT");
}

export function previewDailySchedule(targetDate: string): Promise<SchedulePreview> {
  return request("/api/planner/schedules/preview", { target_date: targetDate });
}

export async function getDailySchedule(targetDate: string): Promise<DailySchedule | null> {
  const response = await request<{ schedule: DailySchedule | null }>(`/api/planner/schedules/day/${targetDate}`, undefined, "GET");
  return response.schedule;
}

export function approveDailySchedule(targetDate: string, idempotencyKey: string, entries: ScheduleEntryProposal[]): Promise<DailySchedule> {
  return request("/api/planner/schedules", {
    target_date: targetDate,
    idempotency_key: idempotencyKey,
    entries: entries.map(({ task_id, start_at, duration_minutes }) => ({ task_id, start_at, duration_minutes })),
  });
}

export function simulateDailySchedule(scenario: WhatIfRequest): Promise<WhatIfResult> {
  return request("/api/planner/schedules/what-if", scenario);
}
