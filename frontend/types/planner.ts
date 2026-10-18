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
