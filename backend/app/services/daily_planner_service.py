from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.planning import DailySchedule, ScheduleEntry, UserPlanningPreference
from app.models.task import Task
from app.schemas.daily_planner import (
    DailyScheduleResponse,
    PlanningPreferencesInput,
    PlanningPreferencesResponse,
    ScheduleEntryResponse,
    SchedulePreviewResponse,
    ScheduleSaveRequest,
    ScheduledTaskProposal,
    UnscheduledTask,
)


DEFAULT_PREFERENCES = {
    "timezone_name": "UTC",
    "workday_start": time(9, 0),
    "workday_end": time(17, 0),
    "preferred_session_minutes": 50,
    "break_minutes": 10,
    "daily_capacity_minutes": 360,
}
MAX_PREVIEW_ENTRIES = 40


def get_preferences(db: Session, user_id: int) -> PlanningPreferencesResponse:
    preferences = db.get(UserPlanningPreference, user_id)
    return PlanningPreferencesResponse.model_validate(preferences or {"user_id": user_id, **DEFAULT_PREFERENCES})


def update_preferences(
    db: Session,
    user_id: int,
    preferences: PlanningPreferencesInput,
) -> PlanningPreferencesResponse:
    row = db.get(UserPlanningPreference, user_id)
    if row is None:
        row = UserPlanningPreference(user_id=user_id, **preferences.model_dump())
        db.add(row)
    else:
        for field, value in preferences.model_dump().items():
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return PlanningPreferencesResponse.model_validate(row)


def _owned_pending_tasks(db: Session, user_id: int) -> list[Task]:
    return list(db.scalars(
        select(Task)
        .join(Goal, Goal.id == Task.goal_id)
        .where(Goal.user_id == user_id, Goal.status == "active", Task.status != "completed")
    ).all())


def _priority_rank(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority.lower(), 1)


def _utc_timestamp(value: datetime | None) -> float:
    if value is None:
        return float("inf")
    normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return normalized.astimezone(timezone.utc).timestamp()


def _deadline_rank(task: Task, target_date: date, timezone_name: str) -> tuple[int, str]:
    if task.deadline is None:
        return 3, "no task deadline"
    deadline = task.deadline
    if deadline.tzinfo is not None:
        deadline_day = deadline.astimezone(ZoneInfo(timezone_name)).date()
    else:
        deadline_day = deadline.date()
    days_left = (deadline_day - target_date).days
    if days_left < 0:
        return 0, "already overdue"
    if days_left <= 2:
        return 1, "deadline within two days"
    if days_left <= 7:
        return 2, "deadline within a week"
    return 3, "deadline is later"


def _explanation(task: Task, target_date: date, timezone_name: str) -> str:
    urgency, urgency_text = _deadline_rank(task, target_date, timezone_name)
    priority = task.priority.lower()
    if urgency == 0:
        return f"Scheduled early because it is {urgency_text}; priority is {priority}."
    if urgency == 1:
        return f"Scheduled early because its {urgency_text}; priority is {priority}."
    if priority == "high":
        return f"Scheduled early because it has high priority; {urgency_text}."
    return f"Ordered by priority and deadline; {urgency_text}."


def preview_daily_schedule(db: Session, user_id: int, target_date: date) -> SchedulePreviewResponse:
    preferences = get_preferences(db, user_id)
    zone = ZoneInfo(preferences.timezone_name)
    tasks = _owned_pending_tasks(db, user_id)
    tasks.sort(key=lambda task: (
        _deadline_rank(task, target_date, preferences.timezone_name)[0],
        _priority_rank(task.priority),
        _utc_timestamp(task.deadline),
        task.position,
        _utc_timestamp(task.created_at),
        task.id,
    ))

    window_start = datetime.combine(target_date, preferences.workday_start, tzinfo=zone)
    window_end = datetime.combine(target_date, preferences.workday_end, tzinfo=zone)
    cursor = window_start
    capacity_left = preferences.daily_capacity_minutes
    scheduled: list[ScheduledTaskProposal] = []
    unscheduled: list[UnscheduledTask] = []

    for task in tasks:
        estimate = task.estimated_minutes or preferences.preferred_session_minutes
        remaining = estimate
        segment_index = 1
        while remaining > 0 and capacity_left > 0 and len(scheduled) < MAX_PREVIEW_ENTRIES:
            duration = min(remaining, preferences.preferred_session_minutes, capacity_left)
            finish = cursor + timedelta(minutes=duration)
            if finish > window_end:
                break
            scheduled.append(ScheduledTaskProposal(
                task_id=task.id,
                title=task.title,
                priority=task.priority,
                segment_index=segment_index,
                start_at=cursor,
                end_at=finish,
                duration_minutes=duration,
                explanation=_explanation(task, target_date, preferences.timezone_name),
            ))
            cursor = finish
            remaining -= duration
            capacity_left -= duration
            segment_index += 1
            if remaining > 0 or capacity_left > 0:
                cursor += timedelta(minutes=preferences.break_minutes)
        if remaining > 0:
            reason = "Working hours or daily capacity are insufficient for the remaining estimate."
            if len(scheduled) >= MAX_PREVIEW_ENTRIES:
                reason = "The schedule reached its 40-session limit; remove lower-priority tasks and rebuild."
            elif task.estimated_minutes is None:
                reason = "Working hours or daily capacity are insufficient for a preferred work session."
            unscheduled.append(UnscheduledTask(
                task_id=task.id,
                title=task.title,
                remaining_minutes=remaining,
                reason=reason,
            ))

    return SchedulePreviewResponse(
        target_date=target_date,
        timezone_name=preferences.timezone_name,
        capacity_minutes=preferences.daily_capacity_minutes,
        scheduled_minutes=sum(item.duration_minutes for item in scheduled),
        entries=scheduled,
        unscheduled=unscheduled,
    )


def save_daily_schedule(
    db: Session,
    user_id: int,
    request: ScheduleSaveRequest,
) -> DailySchedule | None:
    preferences = get_preferences(db, user_id)
    existing = db.scalar(select(DailySchedule).where(
        DailySchedule.user_id == user_id,
        DailySchedule.idempotency_key == str(request.idempotency_key),
    ))
    if existing:
        if existing.target_date != request.target_date:
            raise ValueError("This confirmation key has already been used for another date")
        return existing

    task_ids = {entry.task_id for entry in request.entries}
    tasks = list(db.scalars(
        select(Task)
        .join(Goal, Goal.id == Task.goal_id)
        .where(Task.id.in_(task_ids), Goal.user_id == user_id, Goal.status == "active", Task.status != "completed")
    ).all())
    task_by_id = {task.id: task for task in tasks}
    if len(task_by_id) != len(task_ids):
        raise LookupError("One or more tasks are unavailable")

    zone = ZoneInfo(preferences.timezone_name)
    start_limit = datetime.combine(request.target_date, preferences.workday_start, tzinfo=zone)
    end_limit = datetime.combine(request.target_date, preferences.workday_end, tzinfo=zone)
    entries = sorted(request.entries, key=lambda entry: entry.start_at.astimezone(zone))
    duration_by_task: dict[int, int] = {}
    normalized: list[tuple[object, datetime, datetime, int]] = []
    for entry in entries:
        start_at = entry.start_at.astimezone(zone)
        end_at = start_at + timedelta(minutes=entry.duration_minutes)
        if start_at.date() != request.target_date or start_at < start_limit or end_at > end_limit:
            raise ValueError("Every schedule entry must fit inside the configured workday")
        task = task_by_id[entry.task_id]
        duration_by_task[task.id] = duration_by_task.get(task.id, 0) + entry.duration_minutes
        normalized.append((entry, start_at, end_at, task.id))

    for task_id, total_minutes in duration_by_task.items():
        maximum = task_by_id[task_id].estimated_minutes or preferences.preferred_session_minutes
        if total_minutes > maximum:
            raise ValueError("A task cannot be scheduled for more than its estimated work")

    total_duration = sum(entry.duration_minutes for entry in request.entries)
    if total_duration > preferences.daily_capacity_minutes:
        raise ValueError("Schedule exceeds your daily capacity")
    for previous, current in zip(normalized, normalized[1:]):
        if current[1] < previous[2] + timedelta(minutes=preferences.break_minutes):
            raise ValueError("Schedule entries overlap or do not leave the configured break")

    schedule = DailySchedule(
        user_id=user_id,
        target_date=request.target_date,
        timezone_name=preferences.timezone_name,
        status="approved",
        capacity_minutes=preferences.daily_capacity_minutes,
        idempotency_key=str(request.idempotency_key),
    )
    db.add(schedule)
    try:
        db.flush()
        segment_counts: dict[int, int] = {}
        for entry, start_at, end_at, task_id in normalized:
            segment_counts[task_id] = segment_counts.get(task_id, 0) + 1
            task = task_by_id[task_id]
            db.add(ScheduleEntry(
                schedule_id=schedule.id,
                task_id=task_id,
                segment_index=segment_counts[task_id],
                start_at=start_at,
                end_at=end_at,
                duration_minutes=entry.duration_minutes,
                explanation=_explanation(task, request.target_date, preferences.timezone_name),
            ))
        db.commit()
        db.refresh(schedule)
        return schedule
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(DailySchedule).where(
            DailySchedule.user_id == user_id,
            DailySchedule.idempotency_key == str(request.idempotency_key),
        ))
        if existing and existing.target_date == request.target_date:
            return existing
        raise


def _schedule_response(db: Session, schedule: DailySchedule) -> DailyScheduleResponse:
    rows = db.execute(
        select(ScheduleEntry, Task)
        .join(Task, Task.id == ScheduleEntry.task_id)
        .where(ScheduleEntry.schedule_id == schedule.id)
        .order_by(ScheduleEntry.start_at, ScheduleEntry.id)
    ).all()
    entries = [ScheduleEntryResponse(
        id=entry.id,
        task_id=entry.task_id,
        title=task.title,
        priority=task.priority,
        segment_index=entry.segment_index,
        start_at=entry.start_at,
        end_at=entry.end_at,
        duration_minutes=entry.duration_minutes,
        explanation=entry.explanation,
    ) for entry, task in rows]
    return DailyScheduleResponse(
        id=schedule.id,
        target_date=schedule.target_date,
        timezone_name=schedule.timezone_name,
        status=schedule.status,
        capacity_minutes=schedule.capacity_minutes,
        created_at=schedule.created_at,
        entries=entries,
    )


def read_schedule_by_id(db: Session, user_id: int, schedule_id: int) -> DailyScheduleResponse | None:
    schedule = db.scalar(select(DailySchedule).where(
        DailySchedule.id == schedule_id,
        DailySchedule.user_id == user_id,
    ))
    if schedule is None:
        return None
    return _schedule_response(db, schedule)


def read_daily_schedule(db: Session, user_id: int, target_date: date) -> DailyScheduleResponse | None:
    schedule = db.scalar(select(DailySchedule).where(
        DailySchedule.user_id == user_id,
        DailySchedule.target_date == target_date,
    ).order_by(DailySchedule.created_at.desc(), DailySchedule.id.desc()))
    return _schedule_response(db, schedule) if schedule else None
