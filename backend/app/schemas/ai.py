from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class AIPlanRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)

    @field_validator("goal")
    @classmethod
    def goal_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Goal cannot be blank")
        return value


class PlannedTask(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    priority: Literal["low", "medium", "high"] = "medium"
    estimated_minutes: int = Field(ge=1, le=480)
    position: int = Field(ge=1, le=50)
    deadline_offset_days: int | None = Field(default=None, ge=0, le=3650)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task title cannot be blank")
        return value


class GoalPlan(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    priority: Literal["low", "medium", "high"] = "medium"
    tasks: list[PlannedTask] = Field(min_length=1, max_length=50)
    generation_mode: Literal["openrouter", "rule_based"] = "rule_based"

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Goal title cannot be blank")
        return value

    @model_validator(mode="after")
    def positions_must_be_unique(self):
        positions = [task.position for task in self.tasks]
        if len(set(positions)) != len(positions):
            raise ValueError("Task positions must be unique")
        return self


class AIProviderStatus(BaseModel):
    provider: Literal["openrouter", "deterministic"]
    configured: bool
    fallback_available: bool = True

