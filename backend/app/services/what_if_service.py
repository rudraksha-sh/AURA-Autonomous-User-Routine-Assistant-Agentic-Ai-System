from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.schemas.daily_planner import SchedulePreviewResponse, WhatIfRequest, WhatIfResponse, WhatIfSchedule
from app.services.daily_planner_service import _owned_pending_tasks, get_preferences, schedule_tasks


def _as_what_if_schedule(preview: SchedulePreviewResponse) -> WhatIfSchedule:
    return WhatIfSchedule(
        target_date=preview.target_date,
        timezone_name=preview.timezone_name,
        capacity_minutes=preview.capacity_minutes,
        remaining_minutes=sum(item.remaining_minutes or 0 for item in preview.unscheduled),
        fits=not preview.unscheduled,
        scheduled_minutes=preview.scheduled_minutes,
        entries=[{
            "task_id": None if entry.task_id < 0 else entry.task_id,
            "title": entry.title,
            "priority": entry.priority,
            "segment_index": entry.segment_index,
            "start_at": entry.start_at,
            "end_at": entry.end_at,
            "duration_minutes": entry.duration_minutes,
            "explanation": entry.explanation,
            "is_proposed_task": entry.task_id < 0,
        } for entry in preview.entries],
        unscheduled=[{
            "task_id": None if task.task_id < 0 else task.task_id,
            "title": task.title,
            "remaining_minutes": task.remaining_minutes,
            "reason": task.reason,
            "is_proposed_task": task.task_id < 0,
        } for task in preview.unscheduled],
    )


def _simulate(db: Session, user_id: int, request: WhatIfRequest):
    preferences = get_preferences(db, user_id)
    tasks = {task.id: SimpleNamespace(
        id=task.id, title=task.title, priority=task.priority, estimated_minutes=task.estimated_minutes,
        deadline=task.deadline, position=task.position, created_at=task.created_at,
    ) for task in _owned_pending_tasks(db, user_id)}
    baseline = schedule_tasks(preferences, request.target_date, tasks.values(), respect_deadlines=True)
    if request.capacity_minutes is not None:
        if request.capacity_minutes > preferences.daily_capacity_minutes:
            raise ValueError("A what-if scenario can reduce capacity, but cannot exceed your configured daily capacity")
        preferences = preferences.model_copy(update={"daily_capacity_minutes": request.capacity_minutes})

    change = request.deadline_change
    if change:
        if change.task_id not in tasks:
            raise ValueError("The deadline change requires an owned, pending task.")
        tasks[change.task_id].deadline = change.deadline
    if request.proposed_task is not None:
        tasks[-1] = SimpleNamespace(id=-1, position=-1, created_at=None, **request.proposed_task.model_dump())

    busy = ()
    if request.unavailable_start_at is not None:
        zone = ZoneInfo(preferences.timezone_name)
        start = request.unavailable_start_at.astimezone(timezone.utc)
        end = start + timedelta(minutes=request.unavailable_minutes)
        workday_start, workday_end = (
            datetime.combine(request.target_date, value, tzinfo=zone).astimezone(timezone.utc)
            for value in (preferences.workday_start, preferences.workday_end)
        )
        if start < workday_start or end > workday_end:
            raise ValueError("Unavailable time must fit inside the configured workday on the selected date")
        busy = ((start, end),)
        preferences = preferences.model_copy(update={
            "daily_capacity_minutes": max(0, preferences.daily_capacity_minutes - request.unavailable_minutes),
        })
    simulated = schedule_tasks(preferences, request.target_date, tasks.values(), busy=busy, respect_deadlines=True)
    return baseline, simulated, tasks


def simulate_daily_schedule(db: Session, user_id: int, request: WhatIfRequest) -> WhatIfResponse:
    baseline, simulated, tasks = _simulate(db, user_id, request)
    baseline_remaining = {item.task_id: item.remaining_minutes or 0 for item in baseline.unscheduled}
    no_longer_fit = [
        item.title for item in simulated.unscheduled
        if item.task_id > 0 and (item.remaining_minutes or 0) > baseline_remaining.get(item.task_id, 0)
    ]
    deadline_conflicts: list[str] = []
    for task_id in sorted(item.task_id for item in simulated.unscheduled):
        task = tasks.get(task_id)
        if task and task.deadline:
            due = task.deadline.astimezone(ZoneInfo(simulated.timezone_name)).date() if task.deadline.tzinfo else task.deadline.date()
            if due <= request.target_date + timedelta(days=2):
                deadline_conflicts.append(f"{task.title} may miss its deadline on {due.isoformat()} because it does not fit.")
    explanations = []
    if request.capacity_minutes is not None:
        explanations.append(f"Daily capacity set to {request.capacity_minutes} minutes for this preview.")
    if request.proposed_task is not None:
        explanations.append(f"Added ‘{request.proposed_task.title}’ to this preview only; no task was saved.")
    if request.unavailable_start_at is not None:
        explanations.append(f"Blocked {request.unavailable_minutes} minutes of work time for this preview only.")
    if request.deadline_change:
        explanations.append("Used the proposed deadline for this preview only.")
    explanations.append("This simulation is read-only. Approve a separately reviewed schedule to persist a plan.")
    return WhatIfResponse(
        baseline=_as_what_if_schedule(baseline),
        simulated=_as_what_if_schedule(simulated),
        tasks_no_longer_fit=no_longer_fit,
        potential_deadline_conflicts=deadline_conflicts,
        explanations=explanations,
    )
