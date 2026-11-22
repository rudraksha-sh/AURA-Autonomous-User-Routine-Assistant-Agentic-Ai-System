import type { PlanPreview, SchedulePreview, WhatIfResult } from "@/types/planner";

export type WorkflowOperation = "approve" | "reject" | "pause" | "resume" | "cancel";

export type Workflow = {
  id: string;
  goal_id: number | null;
  status: "awaiting_approval" | "paused" | "cancelled" | "rejected" | "completed" | "undone";
  revision: number;
  created_at: string;
  result: {
    plan: PlanPreview | null;
    schedule: SchedulePreview | null;
    simulation: WhatIfResult | null;
    comparison: {
      previous_run_id: string;
      previous_task_count: number;
      proposed_task_count: number;
      estimated_minutes_change: number;
      overdue_task_count: number;
    } | null;
    trace: { agent: string; outcome: string; at: string }[];
    evidence: { source: string; status: "verified" | null; task_ids: number[] } | null;
  };
};



export type AutonomyGrant = {
  id: string;
  goal_id: number | null;
  status: "active" | "paused" | "revoked" | "expired" | "exhausted" | "consent_required";
  runs_remaining: number;
  task_limit: number;
  expires_at: string;
};

export type AutonomyGrantInput = {
  goal_id: number;
  operation: "goal.tasks.create";
  consent_version: "local-task-grant-v1";
  consent: boolean;
  duration_minutes: number;
  run_limit: number;
  task_limit: number;
};
