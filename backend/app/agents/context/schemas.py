from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.goal import Goal


@dataclass(frozen=True)
class GoalContext:
    goal: Goal
    source: str = "aura.goal"


class SourceReference(BaseModel):
    source_id: str
    version: str
    kind: Literal["goal", "task", "document"]
    chunk: int
    local_id: int | None = None


class ContextPreview(BaseModel):
    schema_version: Literal[1] = 1
    status: Literal["ready", "unavailable"]
    sources: list[SourceReference]


class PlanningGoal(BaseModel):
    id: int
    title: str
    description: str | None
    deadline: datetime | None


class PlanningSnapshot(BaseModel):
    goal: PlanningGoal
    goal_version: str
    retrieval: ContextPreview
    memory_versions: dict[str, str] = Field(default_factory=dict)
