
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: str = Field(default="active", max_length=50)
    priority: str = Field(default="medium", max_length=20)
    deadline: datetime | None = None
    continue_without_asking: bool = False


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, max_length=50)
    priority: str | None = Field(default=None, max_length=20)
    deadline: datetime | None = None
    continue_without_asking: bool | None = None


class GoalResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    status: str
    priority: str
    deadline: datetime | None
    continue_without_asking: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
