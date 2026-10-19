from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    notes: str | None = Field(default=None, max_length=10000)
    status: Literal["pending", "in_progress", "completed"] = "pending"
    priority: Literal["low", "medium", "high"] = "medium"
    estimated_minutes: int | None = Field(default=None, ge=1)
    deadline: datetime | None = None
    position: int = Field(default=1, ge=1)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    notes: str | None = Field(default=None, max_length=10000)
    status: Literal["pending", "in_progress", "completed"] | None = None
    priority: Literal["low", "medium", "high"] | None = None
    estimated_minutes: int | None = Field(default=None, ge=1)
    deadline: datetime | None = None
    position: int | None = Field(default=None, ge=1)


class TaskResponse(BaseModel):
    id: int
    goal_id: int
    title: str
    description: str | None
    notes: str | None = None
    status: str
    priority: str
    estimated_minutes: int | None
    deadline: datetime | None
    position: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskSubtaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    position: int = Field(default=1, ge=1)


class TaskSubtaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    is_completed: bool | None = None
    position: int | None = Field(default=None, ge=1)


class TaskSubtaskResponse(BaseModel):
    id: int
    task_id: int
    title: str
    is_completed: bool
    position: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskActivityResponse(BaseModel):
    id: int
    task_id: int
    action: str
    details: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskBulkAction(BaseModel):
    task_ids: list[int] = Field(min_length=1, max_length=100)
    action: Literal["complete", "delete"]


class TaskBulkActionResponse(BaseModel):
    updated_count: int
    deleted_count: int
    tasks: list[TaskResponse]
