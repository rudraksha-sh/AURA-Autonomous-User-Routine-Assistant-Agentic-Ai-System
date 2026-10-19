from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.schemas.daily_planner import (
    DailyScheduleResponse,
    PlanningPreferencesInput,
    PlanningPreferencesResponse,
    SchedulePreviewRequest,
    SchedulePreviewResponse,
    ScheduleReadResponse,
    ScheduleSaveRequest,
    WhatIfRequest,
    WhatIfResponse,
)
from app.schemas.calendar import CalendarBusyResponse
from app.services.calendar_service import get_calendar_busy_blocks
from app.services.daily_planner_service import (
    delete_daily_schedule,
    get_preferences,
    preview_daily_schedule,
    read_daily_schedule,
    read_schedule_by_id,
    save_daily_schedule,
    update_preferences,
)
from app.services.what_if_service import simulate_daily_schedule


router = APIRouter(prefix="/api/planner", tags=["Daily Planner"])


@router.get("/calendar/events", response_model=CalendarBusyResponse)
def calendar_events(
    start_at: datetime = Query(),
    end_at: datetime = Query(),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if start_at.tzinfo is None or start_at.utcoffset() is None or end_at.tzinfo is None or end_at.utcoffset() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Calendar range must include time zones")
    start_utc = start_at.astimezone(timezone.utc)
    end_utc = end_at.astimezone(timezone.utc)
    if end_utc <= start_utc or end_utc - start_utc > timedelta(days=8):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Calendar range must be positive and no longer than eight days")
    return get_calendar_busy_blocks(db=db, user_id=user_id, start_at=start_at, end_at=end_at)


@router.get("/preferences", response_model=PlanningPreferencesResponse)
def preferences(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_preferences(db, user_id)


@router.put("/preferences", response_model=PlanningPreferencesResponse)
def save_preferences(
    preferences_data: PlanningPreferencesInput,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return update_preferences(db, user_id, preferences_data)


@router.post("/schedules/preview", response_model=SchedulePreviewResponse)
def preview_schedule(
    request: SchedulePreviewRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return preview_daily_schedule(db, user_id, request.target_date)


@router.post("/schedules/what-if", response_model=WhatIfResponse)
def what_if_schedule(
    request: WhatIfRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return simulate_daily_schedule(db, user_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/schedules/day/{target_date}", response_model=ScheduleReadResponse)
def get_schedule(
    target_date: date,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return {"schedule": read_daily_schedule(db, user_id, target_date)}


@router.delete("/schedules/day/{target_date}", status_code=status.HTTP_204_NO_CONTENT)
def clear_schedule(
    target_date: date,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    delete_daily_schedule(db, user_id, target_date)
    return None


@router.post("/schedules", response_model=DailyScheduleResponse, status_code=status.HTTP_201_CREATED)
def approve_schedule(
    request: ScheduleSaveRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        schedule = save_daily_schedule(db, user_id, request)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more tasks are unavailable") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    result = read_schedule_by_id(db, user_id, schedule.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return result
