from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: Literal["pending", "in_progress", "completed"] = "pending"
    priority: Literal["low", "medium", "high"] = "medium"
    estimated_minutes: int | None = Field(default=None, ge=1)
    deadline: datetime | None = None
    position: int = Field(default=1, ge=1)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
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
    status: str
    priority: str
    estimated_minutes: int | None
    deadline: datetime | None
    position: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
