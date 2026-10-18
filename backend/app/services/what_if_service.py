from copy import copy
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.schemas.daily_planner import (
    SchedulePreviewResponse,
    WhatIfRequest,
    WhatIfResponse,
    WhatIfSchedule,
)
from app.services.daily_planner_service import (
    _deadline_rank,
    _explanation,
    _owned_pending_tasks,
    _priority_rank,
    _utc_timestamp,
    get_preferences,
    preview_daily_schedule,
)


def _as_what_if_schedule(preview: SchedulePreviewResponse) -> WhatIfSchedule:
    return WhatIfSchedule(
        target_date=preview.target_date,
        timezone_name=preview.timezone_name,
        capacity_minutes=preview.capacity_minutes,
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


def _simulate(db: Session, user_id: int, request: WhatIfRequest) -> tuple[SchedulePreviewResponse, list[str]]:
    preferences = copy(get_preferences(db, user_id))
    tasks = [copy(task) for task in _owned_pending_tasks(db, user_id)]
    baseline = preview_daily_schedule(db, user_id, request.target_date)
    explanations: list[str] = []

    if request.capacity_minutes is not None:
        if request.capacity_minutes > preferences.daily_capacity_minutes:
            raise ValueError("A what-if scenario can reduce capacity, but cannot exceed your configured daily capacity")
        preferences.daily_capacity_minutes = request.capacity_minutes
        explanations.append(f"Daily work capacity is reduced to {request.capacity_minutes} minutes.")

    if request.proposed_task is not None:
        # Negative IDs are confined to this in-memory simulation and mapped to null in its response.
        tasks.append(SimpleNamespace(
            id=-1,
            title=request.proposed_task.title,
            priority=request.proposed_task.priority,
            estimated_minutes=request.proposed_task.estimated_minutes,
            deadline=request.proposed_task.deadline,
            position=-1,
            created_at=datetime.combine(request.target_date, datetime.min.time(), tzinfo=ZoneInfo("UTC")),
        ))
        explanations.append(f"A proposed {request.proposed_task.priority}-priority task, ‘{request.proposed_task.title}’, is added for simulation only.")

    unavailable: tuple[datetime, datetime] | None = None
    if request.unavailable_start_at is not None:
        zone = ZoneInfo(preferences.timezone_name)
        start = request.unavailable_start_at.astimezone(zone)
        end = start + timedelta(minutes=request.unavailable_minutes or 0)
        workday_start = datetime.combine(request.target_date, preferences.workday_start, tzinfo=zone)
        workday_end = datetime.combine(request.target_date, preferences.workday_end, tzinfo=zone)
        if start.date() != request.target_date or start < workday_start or end > workday_end:
            raise ValueError("Unavailable time must fit inside the configured workday on the selected date")
        unavailable = (start, end)
        reduced_capacity = max(0, preferences.daily_capacity_minutes - (request.unavailable_minutes or 0))
        preferences.daily_capacity_minutes = reduced_capacity
        explanations.append(f"{request.unavailable_minutes} minutes are blocked starting at {start.strftime('%H:%M')} ({preferences.timezone_name}).")

    zone = ZoneInfo(preferences.timezone_name)
    tasks.sort(key=lambda task: (
        _deadline_rank(task, request.target_date, preferences.timezone_name)[0],
        _priority_rank(task.priority),
        _utc_timestamp(task.deadline),
        task.position,
        _utc_timestamp(task.created_at),
        task.id,
    ))
    window_start = datetime.combine(request.target_date, preferences.workday_start, tzinfo=zone)
    window_end = datetime.combine(request.target_date, preferences.workday_end, tzinfo=zone)
    cursor = window_start
    capacity_left = preferences.daily_capacity_minutes
    entries = []
    unscheduled = []

    for task in tasks:
        remaining = task.estimated_minutes or preferences.preferred_session_minutes
        segment_index = 1
        while remaining > 0 and capacity_left > 0 and len(entries) < 40:
            if unavailable and cursor < unavailable[1] and cursor + timedelta(minutes=min(remaining, preferences.preferred_session_minutes, capacity_left)) > unavailable[0]:
                cursor = unavailable[1]
            duration = min(remaining, preferences.preferred_session_minutes, capacity_left)
            finish = cursor + timedelta(minutes=duration)
            if finish > window_end:
                break
            entries.append({
                "task_id": task.id,
                "title": task.title,
                "priority": task.priority,
                "segment_index": segment_index,
                "start_at": cursor,
                "end_at": finish,
                "duration_minutes": duration,
                "explanation": _explanation(task, request.target_date, preferences.timezone_name),
            })
            cursor = finish
            remaining -= duration
            capacity_left -= duration
            segment_index += 1
            if remaining > 0 or capacity_left > 0:
                cursor += timedelta(minutes=preferences.break_minutes)
        if remaining > 0:
            unscheduled.append({
                "task_id": task.id,
                "title": task.title,
                "remaining_minutes": remaining,
                "reason": "Working hours or scenario capacity are insufficient for the remaining estimate.",
            })

    simulated = SchedulePreviewResponse(
        target_date=request.target_date,
        timezone_name=preferences.timezone_name,
        capacity_minutes=preferences.daily_capacity_minutes,
        scheduled_minutes=sum(entry["duration_minutes"] for entry in entries),
        entries=entries,
        unscheduled=unscheduled,
    )
    return baseline, simulated


def simulate_daily_schedule(db: Session, user_id: int, request: WhatIfRequest) -> WhatIfResponse:
    baseline, simulated = _simulate(db, user_id, request)
    baseline_remaining = {item.task_id: item.remaining_minutes or 0 for item in baseline.unscheduled}
    no_longer_fit = [
        item.title for item in simulated.unscheduled
        if item.task_id > 0 and (item.remaining_minutes or 0) > baseline_remaining.get(item.task_id, 0)
    ]
    deadline_conflicts: list[str] = []
    tasks = {task.id: task for task in _owned_pending_tasks(db, user_id)}
    if request.proposed_task is not None:
        tasks[-1] = request.proposed_task
    simulated_unscheduled_ids = {item.task_id for item in simulated.unscheduled}
    for task_id in simulated_unscheduled_ids:
        task = tasks.get(task_id)
        if task and task.deadline:
            due = task.deadline.astimezone(ZoneInfo(simulated.timezone_name)).date() if task.deadline.tzinfo else task.deadline.date()
            if due <= request.target_date + timedelta(days=2):
                deadline_conflicts.append(f"{task.title} may miss its deadline on {due.isoformat()} because it does not fit.")
    if not no_longer_fit:
        no_longer_fit = []
    explanations = []
    if request.capacity_minutes is not None:
        explanations.append(f"Daily capacity set to {request.capacity_minutes} minutes for this preview.")
    if request.proposed_task is not None:
        explanations.append(f"Added ‘{request.proposed_task.title}’ to this preview only; no task was saved.")
    if request.unavailable_start_at is not None:
        explanations.append(f"Blocked {request.unavailable_minutes} minutes of work time for this preview only.")
    explanations.append("This simulation is read-only. Approve a separately reviewed schedule to persist a plan.")
    return WhatIfResponse(
        baseline=_as_what_if_schedule(baseline),
        simulated=_as_what_if_schedule(simulated),
        tasks_no_longer_fit=no_longer_fit,
        potential_deadline_conflicts=deadline_conflicts,
        explanations=explanations,
    )
