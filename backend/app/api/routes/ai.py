from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit_dependencies import (
    ai_limiter,
    enforce_rate_limit,
)
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.schemas.ai import AIPlanRequest, GoalPlan
from app.services.ai_service import create_goal_plan


router = APIRouter(
    prefix="/api/ai",
    tags=["AI"],
)


@router.post(
    "/plan",
    response_model=GoalPlan,
    status_code=status.HTTP_201_CREATED,
)
def generate_plan(
    request: Request,
    plan_request: AIPlanRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(ai_limiter, request)

    _, _, _, plan = create_goal_plan(
        db=db,
        user_id=user_id,
        user_goal=plan_request.goal,
    )

    return plan