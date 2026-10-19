from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.schemas.task import (
    TaskActivityResponse,
    TaskBulkAction,
    TaskBulkActionResponse,
    TaskCreate,
    TaskResponse,
    TaskSubtaskCreate,
    TaskSubtaskResponse,
    TaskSubtaskUpdate,
    TaskUpdate,
)
from app.models.task_detail import TaskSubtask
from app.services.task_service import (
    bulk_task_action,
    create_task_subtask,
    create_task,
    delete_task_subtask,
    delete_task,
    get_goal_tasks,
    get_task,
    get_user_tasks,
    list_task_activity,
    list_task_subtasks,
    update_task_subtask,
    update_task,
)


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


@router.get("", response_model=list[TaskResponse])
def list_user_tasks(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_user_tasks(db=db, user_id=user_id)


@router.post("/bulk", response_model=TaskBulkActionResponse)
def run_bulk_task_action(
    data: TaskBulkAction,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    result = bulk_task_action(db=db, user_id=user_id, task_ids=data.task_ids, action=data.action)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more tasks were not found")
    tasks, updated_count, deleted_count = result
    return {"tasks": tasks, "updated_count": updated_count, "deleted_count": deleted_count}


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


@router.get("/{task_id}/subtasks", response_model=list[TaskSubtaskResponse])
def list_subtasks_for_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not get_task(db=db, user_id=user_id, task_id=task_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return list_task_subtasks(db=db, task_id=task_id)


@router.post("/{task_id}/subtasks", response_model=TaskSubtaskResponse, status_code=status.HTTP_201_CREATED)
def add_subtask_to_task(
    task_id: int,
    data: TaskSubtaskCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not get_task(db=db, user_id=user_id, task_id=task_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return create_task_subtask(db=db, task_id=task_id, data=data)


@router.patch("/{task_id}/subtasks/{subtask_id}", response_model=TaskSubtaskResponse)
def patch_task_subtask(
    task_id: int,
    subtask_id: int,
    data: TaskSubtaskUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not get_task(db=db, user_id=user_id, task_id=task_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    subtask = db.scalar(select(TaskSubtask).where(TaskSubtask.id == subtask_id, TaskSubtask.task_id == task_id))
    if not subtask:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtask not found")
    return update_task_subtask(db=db, subtask=subtask, data=data)


@router.delete("/{task_id}/subtasks/{subtask_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task_subtask(
    task_id: int,
    subtask_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not get_task(db=db, user_id=user_id, task_id=task_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    subtask = db.scalar(select(TaskSubtask).where(TaskSubtask.id == subtask_id, TaskSubtask.task_id == task_id))
    if not subtask:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtask not found")
    delete_task_subtask(db=db, subtask=subtask)
    return None


@router.get("/{task_id}/activity", response_model=list[TaskActivityResponse])
def get_task_activity(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not get_task(db=db, user_id=user_id, task_id=task_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return list_task_activity(db=db, task_id=task_id)


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
