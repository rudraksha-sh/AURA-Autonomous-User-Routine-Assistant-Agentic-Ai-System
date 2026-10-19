from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit_dependencies import (
    ai_limiter,
    enforce_rate_limit,
)
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.schemas.ai import AIPlanRequest, AIProviderStatus, GoalPlan
from app.models.user import User
from app.agents.planner.service import provider_status
from app.services.ai_service import create_goal_plan


router = APIRouter(
    prefix="/api/ai",
    tags=["AI"],
)


@router.get("/status", response_model=AIProviderStatus)
def get_ai_status(
    user_id: int = Depends(get_current_user_id),
):
    # The dependency verifies the user's session; no provider credentials are returned.
    return provider_status()


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

    user = db.get(User, user_id)

    _, _, _, plan = create_goal_plan(
        db=db,
        user_id=user_id,
        user_goal=plan_request.goal,
        use_ai=user.use_ai_planning if user else True,
    )

    return plan
