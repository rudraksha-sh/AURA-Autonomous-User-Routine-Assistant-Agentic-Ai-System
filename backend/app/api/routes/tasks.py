from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.task_service import (
    create_task,
    delete_task,
    get_goal_tasks,
    get_task,
    update_task,
)


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


@router.post(
    "/goals/{goal_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_task(
    goal_id: int,
    task_data: TaskCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    task = create_task(
        db=db,
        user_id=user_id,
        goal_id=goal_id,
        task_data=task_data,
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )

    return task


@router.get(
    "/goals/{goal_id}/tasks",
    response_model=list[TaskResponse],
)
def list_goal_tasks(
    goal_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    tasks = get_goal_tasks(
        db=db,
        user_id=user_id,
        goal_id=goal_id,
    )

    if tasks is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )

    return tasks


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_single_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    task = get_task(
        db=db,
        user_id=user_id,
        task_id=task_id,
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
)
def update_existing_task(
    task_id: int,
    task_data: TaskUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    task = get_task(
        db=db,
        user_id=user_id,
        task_id=task_id,
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return update_task(
        db=db,
        task=task,
        task_data=task_data,
    )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_existing_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    task = get_task(
        db=db,
        user_id=user_id,
        task_id=task_id,
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    delete_task(
        db=db,
        task=task,
    )

    return None