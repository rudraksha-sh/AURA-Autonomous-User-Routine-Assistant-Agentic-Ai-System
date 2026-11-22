import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.replanning.schemas import ConstraintVersion, PlanComparison
from app.models.goal import Goal
from app.models.task import Task
from app.models.workflow import WorkflowRun

VERSION: ConstraintVersion = "goal-plan-v1"


def goal_version(goal: Goal) -> str:
    values = [VERSION, goal.id, goal.title, goal.description, goal.priority, goal.status,
              goal.deadline.isoformat() if goal.deadline else None]
    return hashlib.sha256(json.dumps(values, ensure_ascii=True).encode()).hexdigest()



def compare_plans(db: Session, user_id: int, goal_id: int, previous_run_id: str, plan: dict) -> PlanComparison:
    previous = db.scalar(select(WorkflowRun).where(
        WorkflowRun.id == previous_run_id, WorkflowRun.user_id == user_id, WorkflowRun.goal_id == goal_id,
    ))
    if previous is None or not previous.result.get("plan"):
        raise LookupError("Previous plan not found")
    before = previous.result["plan"]["tasks"]
    after = plan["tasks"]
    overdue = db.scalar(select(func.count(Task.id)).join(Goal, Goal.id == Task.goal_id).where(
        Goal.user_id == user_id, Goal.id == goal_id, Task.status != "completed",
        Task.deadline < datetime.now(timezone.utc),
    ))
    return PlanComparison(
        previous_run_id=previous_run_id, previous_task_count=len(before), proposed_task_count=len(after),
        estimated_minutes_change=sum(item["estimated_minutes"] for item in after)
        - sum(item["estimated_minutes"] for item in before),
        overdue_task_count=overdue,
    )
