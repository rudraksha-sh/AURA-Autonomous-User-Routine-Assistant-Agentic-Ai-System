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

async function request<T>(path: string, body?: unknown, method = "POST", signal?: AbortSignal): Promise<T> {
  const token = getAccessToken();
  if (!token) {
    expireAccessToken();
    throw new PlannerApiError("Authentication required.", 401);
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal,
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

export function startWorkflow(runId: string, goalId: number, targetDate: string, grant?: AutonomyGrant, includeCalendar = false): Promise<Workflow> {
  return request("/api/v1/workflows", {
    intent: "plan_goal", run_id: runId, goal_id: goalId, target_date: targetDate,
    ...(includeCalendar ? { include_calendar: true } : {}),
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

export function startReplan(runId: string, goalId: number, previousRunId: string, targetDate: string, includeCalendar = false): Promise<Workflow> {
  return request("/api/v1/workflows", {
    intent: "plan_goal", run_id: runId, goal_id: goalId, previous_run_id: previousRunId, target_date: targetDate,
    ...(includeCalendar ? { include_calendar: true } : {}),
  });
}

export function resetPlanningPreferences(): Promise<void> {
  return request("/api/planner/preferences", undefined, "DELETE");
}

export type MemoryEntry = { id: string; text: string; use_for_planning: boolean; expires_at: string };
export type MemoryInput = Pick<MemoryEntry, "text" | "use_for_planning"> & { retention_days: number };

export function listMemories(): Promise<MemoryEntry[]> {
  return request("/api/v1/memory", undefined, "GET");
}

export function saveMemory(input: MemoryInput, id?: string): Promise<MemoryEntry> {
  return request(id ? `/api/v1/memory/${id}` : "/api/v1/memory", input, id ? "PUT" : "POST");
}

export function deleteMemory(id?: string): Promise<void> {
  return request(id ? `/api/v1/memory/${id}` : "/api/v1/memory", undefined, "DELETE");
}

export type ReplanSignals = {
  needs_review: boolean;
  changed_task_ids: number[];
  missing_task_ids: number[];
  overdue_task_ids: number[];
  conflicting_task_ids: number[];
};

export type ReceiptStatus = "verified" | "changed" | "failed" | "unknown";

export function getReplanSignals(id: string, signal?: AbortSignal): Promise<ReplanSignals> {
  return request(`/api/v1/workflows/${id}/replan-signals`, undefined, "GET", signal);
}

export function recheckWorkflowReceipt(id: string): Promise<{ status: ReceiptStatus }> {
  return request(`/api/v1/workflows/${id}/verification`, undefined, "GET");
}

export type ExternalAction = {
  id: string;
  goal_id: number | null;
  revision: number;
  state: "preview" | "queued" | "dispatching" | "verified" | "unknown" | "failed";
  consent: "off" | "active" | "paused" | "revoked";
  payload: { start_at: string; duration_minutes: number };
  fingerprint: string;
  consent_version: string;
  adapter_available: boolean;
  effect: string;
};

export type ActionOperation = "confirm" | "pause" | "resume" | "revoke" | "dispatch" | "reconcile";

export function listExternalActions(): Promise<ExternalAction[]> {
  return request("/api/v1/external-actions", undefined, "GET");
}

export function previewExternalAction(requestId: string, goalId: number, startAt: string, minutes: number): Promise<ExternalAction> {
  return request("/api/v1/external-actions", {
    request_id: requestId, goal_id: goalId, provider: "sandbox_calendar", operation: "calendar.hold.create",
    start_at: startAt, duration_minutes: minutes,
  });
}

export function transitionExternalAction(action: ExternalAction, operation: ActionOperation): Promise<ExternalAction> {
  return request(`/api/v1/external-actions/${action.id}/transition`, {
    operation, revision: action.revision,
    ...(operation === "confirm" ? { consent_version: action.consent_version, fingerprint: action.fingerprint } : {}),
  });
}
