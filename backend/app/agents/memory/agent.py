from sqlalchemy.orm import Session

from app.agents.memory.schemas import PlanningPreferencesResponse
from app.models.planning import UserPlanningPreference
from app.services.daily_planner_service import get_preferences


def recall_preferences(db: Session, user_id: int) -> PlanningPreferencesResponse:
    return get_preferences(db, user_id)


def forget_preferences(db: Session, user_id: int) -> None:
    stored = db.get(UserPlanningPreference, user_id)
    if stored is not None:
        db.delete(stored)
        db.commit()
