from pydantic import BaseModel, Field

from pydantic import BaseModel, Field


class AIPlanRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)


class PlannedTask(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: str = Field(default="medium", max_length=20)
    estimated_minutes: int = Field(ge=1)
    position: int = Field(ge=1)
    deadline_offset_days: int | None = Field(default=None, ge=0)


class GoalPlan(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: str = Field(default="medium", max_length=20)
    tasks: list[PlannedTask] = Field(min_length=1, max_length=50)

