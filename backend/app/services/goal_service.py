from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalUpdate


def create_goal(
    db: Session,
    user_id: int,
    goal_data: GoalCreate,
) -> Goal:
    goal = Goal(
        user_id=user_id,
        title=goal_data.title,
        description=goal_data.description,
        status=goal_data.status,
        priority=goal_data.priority,
        deadline=goal_data.deadline,
    )

    db.add(goal)
    db.commit()
    db.refresh(goal)

    return goal


def get_user_goals(
    db: Session,
    user_id: int,
) -> list[Goal]:
    statement = (
        select(Goal)
        .where(Goal.user_id == user_id)
        .order_by(Goal.created_at.asc(), Goal.id.asc())
    )

    return list(db.scalars(statement).all())


def get_goal(
    db: Session,
    user_id: int,
    goal_id: int,
) -> Goal | None:
    statement = select(Goal).where(
        Goal.id == goal_id,
        Goal.user_id == user_id,
    )

    return db.scalar(statement)


def update_goal(
    db: Session,
    goal: Goal,
    goal_data: GoalUpdate,
) -> Goal:
    update_data = goal_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(goal, field, value)

    db.commit()
    db.refresh(goal)

    return goal


def delete_goal(
    db: Session,
    goal: Goal,
) -> None:
    db.delete(goal)
    db.commit()