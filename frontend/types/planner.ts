export type ProposedPlanTask = {
  title: string;
  description: string | null;
  priority: "low" | "medium" | "high";
  estimated_minutes: number;
  deadline: string | null;
  position: number;
};

export type PlanPreview = {
  goal_id: number;
  goal_title: string;
  tasks: ProposedPlanTask[];
};

export type PlanningPreferences = {
  timezone_name: string;
  workday_start: string;
  workday_end: string;
  preferred_session_minutes: number;
  break_minutes: number;
  daily_capacity_minutes: number;
};

export type ScheduleEntryProposal = {
  task_id: number;
  title: string;
  priority: "low" | "medium" | "high";
  segment_index: number;
  start_at: string;
  end_at: string;
  duration_minutes: number;
  explanation: string;
  id?: number;
};

export type UnscheduledTask = {
  task_id: number;
  title: string;
  remaining_minutes: number | null;
  reason: string;
};

export type SchedulePreview = {
  target_date: string;
  timezone_name: string;
  capacity_minutes: number;
  scheduled_minutes: number;
  entries: ScheduleEntryProposal[];
  unscheduled: UnscheduledTask[];
};

export type DailySchedule = {
  id: number;
  target_date: string;
  timezone_name: string;
  status: string;
  capacity_minutes: number;
  created_at: string;
  entries: ScheduleEntryProposal[];
};

export type WhatIfRequest = {
  target_date: string;
  capacity_minutes?: number;
  proposed_task?: { title: string; estimated_minutes: number; priority: "low" | "medium" | "high" };
  unavailable_start_at?: string;
  unavailable_minutes?: number;
};

export type WhatIfSchedule = Omit<SchedulePreview, "entries" | "unscheduled"> & {
  entries: Array<Omit<ScheduleEntryProposal, "task_id"> & { task_id: number | null; is_proposed_task: boolean }>;
  unscheduled: Array<Omit<UnscheduledTask, "task_id"> & { task_id: number | null; is_proposed_task: boolean }>;
};

export type WhatIfResult = {
  baseline: WhatIfSchedule;
  simulated: WhatIfSchedule;
  tasks_no_longer_fit: string[];
  potential_deadline_conflicts: string[];
  explanations: string[];
};
