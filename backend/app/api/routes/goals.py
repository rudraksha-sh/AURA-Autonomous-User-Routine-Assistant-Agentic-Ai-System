from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.schemas.goal import (
    GoalCreate,
    GoalResponse,
    GoalUpdate,
)
from app.services.goal_service import (
    create_goal,
    delete_goal,
    get_goal,
    get_user_goals,
    update_goal,
)


router = APIRouter(
    prefix="/goals",
    tags=["Goals"],
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
    return create_goal(
        db=db,
        user_id=user_id,
        goal_data=goal_data,
    )


@router.get(
    "",
    response_model=list[GoalResponse],
)
def list_goals(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_user_goals(
        db=db,
        user_id=user_id,
    )


@router.get(
    "/{goal_id}",
    response_model=GoalResponse,
)
def get_single_goal(
    goal_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = get_goal(
        db=db,
        user_id=user_id,
        goal_id=goal_id,
    )

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )

    return goal


@router.patch(
    "/{goal_id}",
    response_model=GoalResponse,
)
def update_existing_goal(
    goal_id: int,
    goal_data: GoalUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = get_goal(
        db=db,
        user_id=user_id,
        goal_id=goal_id,
    )

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )

    return update_goal(
        db=db,
        goal=goal,
        goal_data=goal_data,
    )


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_existing_goal(
    goal_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = get_goal(
        db=db,
        user_id=user_id,
        goal_id=goal_id,
    )

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )

    delete_goal(
        db=db,
        goal=goal,
    )

    return None