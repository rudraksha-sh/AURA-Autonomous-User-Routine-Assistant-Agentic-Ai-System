from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.goal import Goal
from app.schemas.planner import PlanRequest, PlanResponse, PlanSaveRequest, SavedPlanResponse
from app.services.planner_service import generate_goal_plan, save_goal_plan


router = APIRouter(prefix="/api/planner", tags=["Planner"])


@router.post("/goals/{goal_id}/plan", response_model=PlanResponse)
def preview_goal_plan(
    goal_id: int,
    request: PlanRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id))
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return generate_goal_plan(goal, request.task_count)


@router.post("/goals/{goal_id}/save", response_model=SavedPlanResponse)
def save_plan(
    goal_id: int,
    request: PlanSaveRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        tasks = save_goal_plan(db, user_id=user_id, goal_id=goal_id, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if tasks is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return {"tasks": tasks}
