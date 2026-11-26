from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agents.context.retrieval import CREDENTIAL
from app.models.memory import PlanningMemory
from app.models.user import User
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


def active_memories(user_id: int):
    return select(PlanningMemory).where(
        PlanningMemory.user_id == user_id, PlanningMemory.expires_at > datetime.now(timezone.utc),
    )


def recall_memory_versions(db: Session, user_id: int) -> dict[str, str]:
    results = db.scalars(active_memories(user_id).where(PlanningMemory.use_for_planning.is_(True))
                         .order_by(PlanningMemory.id).limit(20))
    return {item.id: item.version for item in results}


def check_memory_versions(db: Session, user_id: int, versions: dict[str, str]) -> None:
    if versions:
        rows = db.scalars(active_memories(user_id).where(
            PlanningMemory.id.in_(versions), PlanningMemory.use_for_planning.is_(True),
        ).order_by(PlanningMemory.id).with_for_update(read=True))
        if {item.id: item.version for item in rows} != versions:
            raise ValueError("Planning memory changed after preview. Start a new workflow.")


def save_memory(db: Session, user_id: int, memory_id: str, text: str, use_for_planning: bool, days: int):
    if not text.strip() or "\0" in text or CREDENTIAL.search(text):
        raise ValueError("Planning memory must contain text without credentials.")
    db.scalar(select(User.id).where(User.id == user_id).with_for_update(key_share=True))
    db.execute(delete(PlanningMemory).where(
        PlanningMemory.user_id == user_id, PlanningMemory.expires_at <= datetime.now(timezone.utc),
    ))
    records = list(db.scalars(active_memories(user_id).limit(20)))
    memory = next((record for record in records if record.id == memory_id), None)
    if memory is None:
        if len(records) >= 20:
            raise ValueError("Planning memory limit reached.")
        memory = PlanningMemory(id=memory_id, user_id=user_id)
        db.add(memory)
    memory.text = text.strip()
    memory.version = str(uuid4())
    memory.use_for_planning = use_for_planning
    memory.expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    db.commit()
    return memory
