from datetime import date
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.agents.scheduler.schemas import SchedulePreviewResponse
from app.schemas.planner import PlanResponse
from app.agents.memory.agent import recall_preferences
from app.services.daily_planner_service import read_daily_schedule, schedule_tasks


def schedule_plan(db: Session, user_id: int, target_date: date, plan: PlanResponse) -> SchedulePreviewResponse:
    tasks = [
        SimpleNamespace(id=-task.position, created_at=None, **task.model_dump())
        for task in plan.tasks
    ]
    saved = read_daily_schedule(db, user_id, target_date)
    return schedule_tasks(
        recall_preferences(db, user_id), target_date, tasks,
        reserved=tuple(saved.entries) if saved else (),
    )
