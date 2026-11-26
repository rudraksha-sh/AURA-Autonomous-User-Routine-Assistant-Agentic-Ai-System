from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.verification.schemas import VerificationReceipt
from app.models.goal import Goal
from app.models.task import Task
from app.tools.recovery import snapshot_task


def verify_tasks(
    db: Session, user_id: int, goal_id: int | None, task_ids: list[int],
    expected: dict[str, str] | None = None,
) -> VerificationReceipt:
    tasks = list(db.scalars(select(Task).join(Goal, Goal.id == Task.goal_id).where(
        Goal.user_id == user_id, Goal.id == goal_id, Task.id.in_(task_ids),
    ).order_by(Task.id)))
    found = [task.id for task in tasks]
    missing = sorted(set(task_ids) - set(found))
    has_evidence = bool(task_ids and expected and set(expected) == {str(value) for value in task_ids})
    changed = [task.id for task in tasks if snapshot_task(task) != expected[str(task.id)]] if has_evidence else []
    if missing:
        status = "failed"
    elif not has_evidence:
        status = "unknown"
    else:
        status = "changed" if changed else "verified"
    return VerificationReceipt(status=status, task_ids=found, changed_task_ids=changed, missing_task_ids=missing,
                               evidence_version="task-fingerprint-v1" if has_evidence else None)
