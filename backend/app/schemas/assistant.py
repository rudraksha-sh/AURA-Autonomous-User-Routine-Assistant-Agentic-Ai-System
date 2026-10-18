from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.goal import GoalResponse
from app.schemas.task import TaskResponse


class ListGoalsTool(BaseModel):
    tool: Literal["list_goals"]


class ListTasksTool(BaseModel):
    tool: Literal["list_tasks"]


class CreateGoalTool(BaseModel):
    tool: Literal["create_goal"]
    idempotency_key: UUID
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Goal title cannot be blank")
        return value


class CreateTaskTool(BaseModel):
    tool: Literal["create_task"]
    idempotency_key: UUID
    goal_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task title cannot be blank")
        return value


class CompleteTaskTool(BaseModel):
    tool: Literal["complete_task"]
    idempotency_key: UUID
    task_id: int = Field(gt=0)


AssistantToolRequest = Annotated[
    Union[ListGoalsTool, ListTasksTool, CreateGoalTool, CreateTaskTool, CompleteTaskTool],
    Field(discriminator="tool"),
]


class AssistantToolResponse(BaseModel):
    tool: str
    goals: list[GoalResponse] | None = None
    tasks: list[TaskResponse] | None = None
    result: GoalResponse | TaskResponse | None = None
    replayed: bool = False
