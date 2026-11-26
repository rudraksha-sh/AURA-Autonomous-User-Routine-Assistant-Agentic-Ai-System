from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.agents.memory.agent import recall_preferences
from app.agents.scheduler.schemas import SchedulePreviewResponse
from app.integrations.google.reads import GoogleReadError, free_busy
from app.schemas.planner import PlanResponse
from app.services.daily_planner_service import _owned_pending_tasks, _utc_timestamp, read_daily_schedule, schedule_tasks


def schedule_plan(
    db: Session, user_id: int, target_date: date, plan: PlanResponse, *,
    include_calendar: bool = False, reconciliation: dict | None = None,
) -> SchedulePreviewResponse:
    preferences = recall_preferences(db, user_id)
    saved = read_daily_schedule(db, user_id, target_date)
    reserved = tuple(saved.entries) if saved else ()
    reconciliation = reconciliation or {}
    updates = reconciliation.get("updates", {})
    reserved_ids = {entry.task_id for entry in reserved}
    excluded = reserved_ids | {int(value) for value in updates.values()}
    tasks = [task for task in _owned_pending_tasks(db, user_id) if task.id not in excluded]
    for task in plan.tasks:
        task_id = int(updates.get(str(task.position), -task.position))
        if task.position not in reconciliation.get("skipped", ()) and task_id not in reserved_ids:
            tasks.append(SimpleNamespace(id=task_id, created_at=None, **task.model_dump()))
    busy = ()
    status = "not_requested"
    if include_calendar:
        zone = ZoneInfo(preferences.timezone_name)
        start, end = (datetime.combine(target_date, time, tzinfo=zone)
                      for time in (preferences.workday_start, preferences.workday_end))
        try:
            busy = tuple(free_busy(db, user_id, start, end))
            status = "included"
        except (PermissionError, GoogleReadError):
            status = "unavailable"
    preview = schedule_tasks(preferences, target_date, tasks, reserved=reserved, busy=busy, respect_deadlines=True)
    conflicts = {
        item.task_id for item in reserved
        if any(start.timestamp() < _utc_timestamp(item.end_at) and end.timestamp() > _utc_timestamp(item.start_at)
               for start, end in busy)
    }
    return preview.model_copy(update={"calendar_status": status, "calendar_conflict_task_ids": sorted(conflicts)})
