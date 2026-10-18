export type Task = {
  id: number;
  goal_id: number;
  title: string;
  description: string | null;
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
  status?: string;
  priority?: string;
  estimated_minutes?: number | null;
  deadline?: string | null;
  position?: number;
};

export type UpdateTaskInput = Partial<CreateTaskInput>;
