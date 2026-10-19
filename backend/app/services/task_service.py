from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.task import Task
from app.models.task_detail import TaskActivity, TaskSubtask
from app.schemas.task import TaskCreate, TaskSubtaskCreate, TaskSubtaskUpdate, TaskUpdate


def _record_activity(db: Session, task_id: int, action: str, details: dict | None = None) -> None:
    db.add(TaskActivity(task_id=task_id, action=action, details=details or {}))


def create_task(
    db: Session,
    user_id: int,
    goal_id: int,
    task_data: TaskCreate,
) -> Task | None:
    goal = db.scalar(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.user_id == user_id,
        )
    )

    if not goal:
        return None

    task = Task(
        goal_id=goal_id,
        title=task_data.title,
        description=task_data.description,
        notes=task_data.notes,
        status=task_data.status,
        priority=task_data.priority,
        estimated_minutes=task_data.estimated_minutes,
        deadline=task_data.deadline,
        position=task_data.position,
    )

    db.add(task)
    db.flush()
    _record_activity(db, task.id, "created", {"title": task.title})
    db.commit()
    db.refresh(task)

    return task


def get_goal_tasks(
    db: Session,
    user_id: int,
    goal_id: int,
) -> list[Task] | None:
    goal = db.scalar(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.user_id == user_id,
        )
    )

    if not goal:
        return None

    statement = (
        select(Task)
        .where(Task.goal_id == goal_id)
        .order_by(Task.position, Task.created_at)
    )

    return list(db.scalars(statement).all())


def get_user_tasks(db: Session, user_id: int) -> list[Task]:
    statement = (
        select(Task)
        .join(Goal, Task.goal_id == Goal.id)
        .where(Goal.user_id == user_id)
        .order_by(Task.deadline, Task.position, Task.created_at)
    )
    return list(db.scalars(statement).all())


def get_task(
    db: Session,
    user_id: int,
    task_id: int,
) -> Task | None:
    statement = (
        select(Task)
        .join(Goal, Task.goal_id == Goal.id)
        .where(
            Task.id == task_id,
            Goal.user_id == user_id,
        )
    )

    return db.scalar(statement)


def update_task(
    db: Session,
    task: Task,
    task_data: TaskUpdate,
) -> Task:
    update_data = task_data.model_dump(exclude_unset=True)
    previous_status = task.status
    changed_fields = sorted(update_data)

    for field, value in update_data.items():
        setattr(task, field, value)

    if "status" in update_data and task.status != previous_status:
        _record_activity(db, task.id, "status_changed", {"from": previous_status, "to": task.status})
    elif changed_fields:
        _record_activity(db, task.id, "updated", {"fields": changed_fields})
    db.commit()
    db.refresh(task)

    return task


def delete_task(
    db: Session,
    task: Task,
) -> None:
    db.delete(task)
    db.commit()


def bulk_task_action(db: Session, user_id: int, task_ids: list[int], action: str) -> tuple[list[Task], int, int] | None:
    ids = set(task_ids)
    tasks = list(db.scalars(select(Task).join(Goal).where(Goal.user_id == user_id, Task.id.in_(ids))).all())
    if len(tasks) != len(ids):
        return None
    updated_count = 0
    deleted_count = 0
    if action == "complete":
        for task in tasks:
            if task.status != "completed":
                previous_status = task.status
                task.status = "completed"
                _record_activity(db, task.id, "status_changed", {"from": previous_status, "to": "completed"})
                updated_count += 1
        db.commit()
        for task in tasks:
            db.refresh(task)
        return tasks, updated_count, deleted_count
    for task in tasks:
        db.delete(task)
        deleted_count += 1
    db.commit()
    return [], updated_count, deleted_count


def list_task_subtasks(db: Session, task_id: int) -> list[TaskSubtask]:
    return list(db.scalars(select(TaskSubtask).where(TaskSubtask.task_id == task_id).order_by(TaskSubtask.position, TaskSubtask.id)).all())


def create_task_subtask(db: Session, task_id: int, data: TaskSubtaskCreate) -> TaskSubtask:
    subtask = TaskSubtask(task_id=task_id, title=data.title.strip(), position=data.position)
    db.add(subtask)
    db.flush()
    _record_activity(db, task_id, "subtask_added", {"subtask_id": subtask.id, "title": subtask.title})
    db.commit()
    db.refresh(subtask)
    return subtask


def update_task_subtask(db: Session, subtask: TaskSubtask, data: TaskSubtaskUpdate) -> TaskSubtask:
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(subtask, field, value)
    if changes:
        _record_activity(db, subtask.task_id, "subtask_updated", {"subtask_id": subtask.id, "fields": sorted(changes)})
    db.commit()
    db.refresh(subtask)
    return subtask


def delete_task_subtask(db: Session, subtask: TaskSubtask) -> None:
    task_id = subtask.task_id
    subtask_id = subtask.id
    title = subtask.title
    db.delete(subtask)
    _record_activity(db, task_id, "subtask_deleted", {"subtask_id": subtask_id, "title": title})
    db.commit()


def list_task_activity(db: Session, task_id: int) -> list[TaskActivity]:
    return list(db.scalars(select(TaskActivity).where(TaskActivity.task_id == task_id).order_by(TaskActivity.created_at.desc(), TaskActivity.id.desc()).limit(100)).all())
