import type { AutonomyGrant, AutonomyGrantInput, Workflow, WorkflowOperation } from "@/types/workflow";
import { expireAccessToken, getAccessToken } from "@/services/auth-storage";
import type { Task } from "@/types/task";
import type { CalendarEventsResponse, DailySchedule, PlanPreview, PlanningPreferences, ProposedPlanTask, ScheduleEntryProposal, SchedulePreview, WhatIfRequest, WhatIfResult } from "@/types/planner";

const API_BASE_URL = "";

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
    const detail = payload?.detail ?? payload?.message ?? `Request failed (${response.status}).`;
    throw new PlannerApiError(String(detail), response.status);
  }
  if (response.status === 204) return undefined as T;
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

export function deleteDailySchedule(targetDate: string): Promise<void> {
  return request(`/api/planner/schedules/day/${targetDate}`, undefined, "DELETE");
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

export function getCalendarEvents(startAt: string, endAt: string): Promise<CalendarEventsResponse> {
  const query = new URLSearchParams({ start_at: startAt, end_at: endAt });
  return request(`/api/planner/calendar/events?${query.toString()}`, undefined, "GET");
}


export function listWorkflows(): Promise<Workflow[]> {
  return request("/api/v1/workflows", undefined, "GET");
}

export function startWorkflow(runId: string, goalId: number, targetDate: string, grant?: AutonomyGrant): Promise<Workflow> {
  return request("/api/v1/workflows", {
    intent: "plan_goal", run_id: runId, goal_id: goalId, target_date: targetDate,
    ...(grant ? { grant_id: grant.id, task_count: grant.task_limit } : {}),
  });
}

export function transitionWorkflow(workflow: Workflow, operation: WorkflowOperation): Promise<Workflow> {
  return request(`/api/v1/workflows/${workflow.id}/transition`, { operation, revision: workflow.revision });
}



export function listAutonomyGrants(): Promise<AutonomyGrant[]> {
  return request("/api/v1/autonomy/grants", undefined, "GET");
}

export function createAutonomyGrant(input: AutonomyGrantInput): Promise<AutonomyGrant> {
  return request("/api/v1/autonomy/grants", input);
}

export function transitionAutonomyGrant(id: string, operation: "pause" | "resume" | "revoke"): Promise<AutonomyGrant> {
  return request(`/api/v1/autonomy/grants/${id}/transition`, { operation });
}

export function stopAutonomy(): Promise<void> {
  return request("/api/v1/autonomy/stop");
}



export function undoWorkflow(workflow: Workflow): Promise<Workflow> {
  return request(`/api/v1/workflows/${workflow.id}/undo`, { confirm: true, revision: workflow.revision });
}



export function startSimulationWorkflow(runId: string, scenario: WhatIfRequest): Promise<Workflow> {
  return request("/api/v1/workflows", { intent: "simulate", run_id: runId, scenario });
}

export function startReplan(runId: string, goalId: number, previousRunId: string, targetDate: string): Promise<Workflow> {
  return request("/api/v1/workflows", {
    intent: "plan_goal", run_id: runId, goal_id: goalId, previous_run_id: previousRunId, target_date: targetDate,
  });
}

export function resetPlanningPreferences(): Promise<void> {
  return request("/api/planner/preferences", undefined, "DELETE");
}
