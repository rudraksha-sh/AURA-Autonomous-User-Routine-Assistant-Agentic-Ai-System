import type { Goal } from "@/types/goal";
import type { Task } from "@/types/task";

export function getTaskScore(task: Task, goal?: Goal, now = new Date()) {
  const priority = task.priority.toLowerCase() === "high" ? 30 : task.priority.toLowerCase() === "medium" ? 20 : 10;
  let urgency = 0;
  if (task.deadline) {
    const deadline = new Date(task.deadline);
    if (!Number.isNaN(deadline.getTime())) {
      const dueDay = new Date(deadline.getFullYear(), deadline.getMonth(), deadline.getDate());
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const days = Math.round((dueDay.getTime() - today.getTime()) / 86_400_000);
      urgency = days < 0 ? 45 : days === 0 ? 40 : days <= 7 ? 25 : days <= 30 ? 15 : 5;
    }
  }
  const quickWin = task.estimated_minutes && task.estimated_minutes <= 30 ? 10 : 0;
  const goalPriority = goal?.priority.toLowerCase() === "high" ? 10 : goal?.priority.toLowerCase() === "medium" ? 5 : 0;
  return Math.min(100, priority + urgency + quickWin + goalPriority);
}
