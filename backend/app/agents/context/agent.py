from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.context.schemas import GoalContext
from app.models.goal import Goal


def load_goal(db: Session, user_id: int, goal_id: int, *, lock: bool = False) -> GoalContext:
    query = select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    goal = db.scalar(query.with_for_update(key_share=True) if lock else query)
    if goal is None:
        raise LookupError("Goal not found")
    return GoalContext(goal)

