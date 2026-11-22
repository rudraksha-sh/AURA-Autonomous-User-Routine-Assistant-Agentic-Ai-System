from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.verification.schemas import VerificationReceipt
from app.models.goal import Goal
from app.models.task import Task


def verify_tasks(db: Session, user_id: int, goal_id: int | None, task_ids: list[int]) -> VerificationReceipt:
    found = set(db.scalars(
        select(Task.id).join(Goal, Goal.id == Task.goal_id).where(
            Goal.user_id == user_id, Goal.id == goal_id, Task.id.in_(task_ids)
        )
    ))
    verified = bool(task_ids) and found == set(task_ids)
    return VerificationReceipt(status="verified" if verified else "unverified", task_ids=sorted(found))
