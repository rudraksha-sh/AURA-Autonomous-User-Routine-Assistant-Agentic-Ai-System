from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.agents.execution.schemas import CREATE_GOAL_TASKS
from app.models.autonomy import AutonomyGrant

CONSENT_VERSION = "local-task-grant-v1"


def consume_grant(db: Session, grant_id: str, user_id: int, goal_id: int, task_count: int) -> None:
    """Reserve one execution in the same transaction as its effect and receipt."""
    result = db.execute(update(AutonomyGrant).where(
        AutonomyGrant.id == grant_id,
        AutonomyGrant.user_id == user_id,
        AutonomyGrant.goal_id == goal_id,
        AutonomyGrant.operation == CREATE_GOAL_TASKS,
        AutonomyGrant.consent_version == CONSENT_VERSION,
        AutonomyGrant.status == "active",
        AutonomyGrant.expires_at > datetime.now(timezone.utc),
        AutonomyGrant.runs_remaining > 0,
        AutonomyGrant.task_limit >= task_count,
    ).values(runs_remaining=AutonomyGrant.runs_remaining - 1))
    if result.rowcount != 1:
        raise PermissionError("The autonomous grant does not permit this goal, action, or task count.")
