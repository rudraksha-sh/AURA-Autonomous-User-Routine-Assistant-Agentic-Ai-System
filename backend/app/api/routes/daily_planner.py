from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
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
from app.services.daily_planner_service import (
    get_preferences,
    preview_daily_schedule,
    read_daily_schedule,
    read_schedule_by_id,
    save_daily_schedule,
    update_preferences,
)
from app.services.what_if_service import simulate_daily_schedule


router = APIRouter(prefix="/api/planner", tags=["Daily Planner"])


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
