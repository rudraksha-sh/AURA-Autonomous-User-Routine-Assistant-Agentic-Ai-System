
import logging
from datetime import datetime, time, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.goal import Goal
from app.models.planning import DailySchedule
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalResponse, GoalUpdate
from app.schemas.planner import PlanSaveRequest, ProposedTask
from app.schemas.daily_planner import ScheduleSaveEntry, ScheduleSaveRequest
from app.services.goal_service import (
    create_goal,
    delete_goal,
    get_goal,
    get_user_goals,
    update_goal,
)
from app.agents.planner.service import generate_goal_plan as generate_ai_goal_plan
from app.services.planner_service import save_goal_plan
from app.services.daily_planner_service import (
    get_preferences,
    preview_daily_schedule,
    save_daily_schedule,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/goals", tags=["Goals"])


def _generate_and_save_tasks(
    db: Session,
    user_id: int,
    goal: Goal,
) -> list:
    user = db.get(User, user_id)
    use_ai = user.use_ai_planning if user else True

    plan = generate_ai_goal_plan(
        f"Goal title: {goal.title}\n"
        f"Goal description: {goal.description or 'Not provided'}",
        use_ai=use_ai,
    )

    current_day = datetime.now(timezone.utc).date()
    due_date = goal.deadline.date() if goal.deadline else None
    if due_date is not None and due_date < current_day:
        due_date = None

    span = max((due_date - current_day).days, 1) if due_date else 0
    proposed_tasks = []

    for index, task in enumerate(plan.tasks[:5], start=1):
        deadline = None

        if due_date:
            day_offset = task.deadline_offset_days
            if day_offset is None:
                day_offset = max(1, round(span * index / 5))

            suggested_day = min(
                current_day + timedelta(days=day_offset),
                due_date,
            )
            if suggested_day <= current_day:
                suggested_day = current_day + timedelta(days=1)

            deadline = datetime.combine(
                suggested_day,
                time(17, 0),
                tzinfo=timezone.utc,
            )

        proposed_tasks.append(
            ProposedTask(
                title=task.title,
                description=task.description,
                priority=task.priority,
                estimated_minutes=max(5, min(task.estimated_minutes, 480)),
                deadline=deadline,
                position=index,
            )
        )

    if len(proposed_tasks) < 3:
        raise RuntimeError("The planner returned fewer than three tasks.")

    saved_tasks = save_goal_plan(
        db,
        user_id=user_id,
        goal_id=goal.id,
        request=PlanSaveRequest(
            idempotency_key=uuid4(),
            tasks=proposed_tasks,
        ),
    )

    if saved_tasks is None:
        raise RuntimeError("The goal could not be found while saving its plan.")

    return saved_tasks


def _schedule_new_tasks(
    db: Session,
    user_id: int,
    task_ids: set[int],
) -> None:
    if not task_ids:
        return

    preferences = get_preferences(db, user_id)
    zone = ZoneInfo(preferences.timezone_name)
    first_day = datetime.now(zone).date()

    # Do not create a second schedule for a date that already has one.
    existing_dates = set(
        db.scalars(
            select(DailySchedule.target_date).where(
                DailySchedule.user_id == user_id,
                DailySchedule.target_date >= first_day,
                DailySchedule.target_date <= first_day + timedelta(days=30),
            )
        ).all()
    )

    target_date = next(
        (
            first_day + timedelta(days=offset)
            for offset in range(31)
            if first_day + timedelta(days=offset) not in existing_dates
        ),
        None,
    )

    if target_date is None:
        raise RuntimeError(
            "No unscheduled date was found in the next 31 days."
        )

    preview = preview_daily_schedule(
        db,
        user_id,
        target_date,
        task_ids=task_ids,
    )

    if not preview.entries:
        # Tasks remain saved and can be scheduled manually later.
        logger.info(
            "No new goal tasks fit on %s for user %s.",
            target_date,
            user_id,
        )
        return

    save_daily_schedule(
        db,
        user_id,
        ScheduleSaveRequest(
            idempotency_key=uuid4(),
            target_date=target_date,
            entries=[
                ScheduleSaveEntry(
                    task_id=entry.task_id,
                    start_at=entry.start_at,
                    duration_minutes=entry.duration_minutes,
                )
                for entry in preview.entries
            ],
        ),
    )


@router.post(
    "",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_goal(
    goal_data: GoalCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = create_goal(db=db, user_id=user_id, goal_data=goal_data)

    if not goal_data.continue_without_asking:
        return goal

    try:
        tasks = _generate_and_save_tasks(db, user_id, goal)
    except Exception as exc:
        logger.exception(
            "Automatic planning failed for goal %s belonging to user %s",
            goal.id,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"Goal {goal.id} was created, but automatic planning failed. "
                "The goal remains saved. Refresh your goals before retrying."
            ),
        ) from exc

    try:
        _schedule_new_tasks(
            db,
            user_id,
            {task.id for task in tasks},
        )
    except Exception as exc:
        logger.exception(
            "Automatic scheduling failed for goal %s belonging to user %s",
            goal.id,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Goal {goal.id} and its tasks were saved, but automatic "
                "scheduling failed. Refresh your tasks before retrying."
            ),
        ) from exc

    return goal


@router.get("", response_model=list[GoalResponse])
def list_goals(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_user_goals(db=db, user_id=user_id)


@router.get("/{goal_id}", response_model=GoalResponse)
def get_single_goal(
    goal_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = get_goal(db=db, user_id=user_id, goal_id=goal_id)
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )
    return goal


@router.patch("/{goal_id}", response_model=GoalResponse)
def update_existing_goal(
    goal_id: int,
    goal_data: GoalUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = get_goal(db=db, user_id=user_id, goal_id=goal_id)
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )
    return update_goal(db=db, goal=goal, goal_data=goal_data)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_goal(
    goal_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = get_goal(db=db, user_id=user_id, goal_id=goal_id)
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )

    delete_goal(db=db, goal=goal)
    return None
