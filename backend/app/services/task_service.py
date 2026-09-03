from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


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
        status=task_data.status,
        priority=task_data.priority,
        estimated_minutes=task_data.estimated_minutes,
        deadline=task_data.deadline,
        position=task_data.position,
    )

    db.add(task)
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

    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


def delete_task(
    db: Session,
    task: Task,
) -> None:
    db.delete(task)
    db.commit()