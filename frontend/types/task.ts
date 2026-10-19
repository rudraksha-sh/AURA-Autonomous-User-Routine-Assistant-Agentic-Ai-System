export type Task = {
  id: number;
  goal_id: number;
  title: string;
  description: string | null;
  notes: string | null;
  status: string;
  priority: string;
  estimated_minutes: number | null;
  deadline: string | null;
  position: number;
  created_at: string;
  updated_at: string;
};

export type CreateTaskInput = {
  title: string;
  description?: string | null;
  notes?: string | null;
  status?: string;
  priority?: string;
  estimated_minutes?: number | null;
  deadline?: string | null;
  position?: number;
};

export type UpdateTaskInput = Partial<CreateTaskInput>;

export type TaskSubtask = {
  id: number;
  task_id: number;
  title: string;
  is_completed: boolean;
  position: number;
  created_at: string;
  updated_at: string;
};

export type TaskActivity = {
  id: number;
  task_id: number;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type TaskBulkActionResult = {
  updated_count: number;
  deleted_count: number;
  tasks: Task[];
};
