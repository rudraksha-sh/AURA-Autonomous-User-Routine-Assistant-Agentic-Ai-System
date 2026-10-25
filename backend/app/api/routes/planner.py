from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.goal import Goal
from app.models.user import User
from app.schemas.planner import PlanRequest, PlanResponse, PlanSaveRequest, ProposedTask, SavedPlanResponse
from app.services.planner_service import save_goal_plan
from app.agents.planner.service import generate_goal_plan as generate_ai_goal_plan


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

    user = db.get(User, user_id)
    use_ai = user.use_ai_planning if user else False

    goal_context = f"Goal title: {goal.title}\nGoal description: {goal.description or 'Not provided'}"
    plan = generate_ai_goal_plan(goal_context, use_ai=use_ai)

    proposed_tasks = []
    current_day = datetime.now(timezone.utc).date()
    due_date = goal.deadline.date() if goal.deadline else None
    if due_date is not None and due_date < current_day:
        due_date = None
    span = max((due_date - current_day).days, 1) if due_date else 0

    for index, task in enumerate(plan.tasks[:request.task_count], start=1):
        deadline = None
        if due_date:
            day_offset = task.deadline_offset_days
            if day_offset is None:
                day_offset = max(1, round(span * index / request.task_count))
            suggested_day = min(current_day + timedelta(days=day_offset), due_date)
            if suggested_day <= current_day:
                suggested_day = current_day + timedelta(days=1)
            deadline = datetime.combine(suggested_day, time(17, 0), tzinfo=timezone.utc)

        proposed_tasks.append(ProposedTask(
            title=task.title,
            description=task.description,
            priority=task.priority,
            estimated_minutes=max(5, min(task.estimated_minutes, 480)),
            deadline=deadline,
            position=index,
        ))

    if len(proposed_tasks) < 3:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The planner did not generate enough tasks. Please try again.",
        )

    return PlanResponse(
        goal_id=goal.id,
        goal_title=goal.title,
        generation_mode=plan.generation_mode,
        tasks=proposed_tasks,
    )


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
