
export type GoalStatus = "active" | "completed" | "archived";
export type GoalPriority = "low" | "medium" | "high";

export type Goal = {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  deadline: string | null;
  continue_without_asking: boolean;
  created_at: string;
  updated_at: string;
};

export type CreateGoalInput = {
  title: string;
  description?: string | null;
  status?: string;
  priority?: string;
  deadline?: string | null;
  continue_without_asking?: boolean;
};

export type UpdateGoalInput = {
  title?: string;
  description?: string | null;
  status?: string;
  priority?: string;
  deadline?: string | null;
  continue_without_asking?: boolean;
};
