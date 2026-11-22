import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.planning import ScheduleEntry
from app.models.task import Task
from app.models.task_detail import TaskActivity, TaskSubtask


def snapshot_task(task: Task) -> str:
    data = [
        task.id, task.goal_id, task.title, task.description, task.notes, task.status,
        task.priority, task.estimated_minutes, task.position,
        task.deadline.isoformat() if task.deadline else None,
        task.created_at.isoformat(), task.updated_at.isoformat(),
    ]
    return hashlib.sha256(json.dumps(data, ensure_ascii=True).encode()).hexdigest()


def remove_unchanged_workflow_tasks(
    db: Session, user_id: int, goal_id: int, expected_snapshots: dict[str, str],
) -> None:
    ids = [int(value) for value in expected_snapshots]
    tasks = list(db.scalars(select(Task).join(Goal, Goal.id == Task.goal_id).where(
        Goal.user_id == user_id, Goal.id == goal_id, Task.id.in_(ids),
    ).order_by(Task.id).with_for_update(of=Task)))
    if not tasks or {str(task.id): snapshot_task(task) for task in tasks} != expected_snapshots:
        raise ValueError("Tasks have changed or are unavailable. Review them in your task list.")
    for model in (ScheduleEntry, TaskSubtask, TaskActivity):
        if db.scalar(select(model.id).where(model.task_id.in_(ids)).limit(1)) is not None:
            raise ValueError("Tasks contain activity, subtasks, or schedule entries. Review them in your task list.")
    for task in tasks:
        db.delete(task)
    db.flush()
