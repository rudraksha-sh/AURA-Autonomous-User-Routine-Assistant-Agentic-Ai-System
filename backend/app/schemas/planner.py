from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.task import TaskResponse


Priority = Literal["low", "medium", "high"]


class PlanRequest(BaseModel):
    task_count: int = Field(default=5, ge=3, le=8)


class ProposedTask(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    priority: Priority = "medium"
    estimated_minutes: int = Field(ge=5, le=480)
    deadline: datetime | None = None
    position: int = Field(ge=1, le=8)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task title cannot be blank")
        return value

    @field_validator("deadline")
    @classmethod
    def deadline_must_not_be_in_the_past(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        if normalized < datetime.now(timezone.utc):
            raise ValueError("Suggested deadline must be in the future")
        return value


class PlanResponse(BaseModel):
    goal_id: int
    goal_title: str
    tasks: list[ProposedTask] = Field(min_length=3, max_length=8)


class PlanSaveRequest(BaseModel):
    idempotency_key: UUID
    tasks: list[ProposedTask] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def positions_must_be_unique(self):
        positions = [task.position for task in self.tasks]
        if len(set(positions)) != len(positions):
            raise ValueError("Task positions must be unique")
        return self


class SavedPlanResponse(BaseModel):
    tasks: list[TaskResponse]
