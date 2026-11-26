from datetime import date, datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.agents.context.schemas import ContextPreview
from app.agents.replanning.schemas import PlanComparison
from app.agents.intelligence.schemas import CapacityFinding
from app.schemas.daily_planner import SchedulePreviewResponse, WhatIfRequest, WhatIfResponse


def _timestamp_with_zone(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


UtcTimestamp = Annotated[datetime, AfterValidator(_timestamp_with_zone)]


class PlanStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal["plan_goal"]
    run_id: UUID
    goal_id: int = Field(gt=0)
    grant_id: UUID | None = None
    previous_run_id: UUID | None = None
    target_date: date
    task_count: int = Field(default=5, ge=3, le=8)
    include_calendar: bool = False

    @model_validator(mode="after")
    def replans_require_review(self):
        if self.previous_run_id and self.grant_id:
            raise ValueError("Replanning requires individual approval.")
        return self


class SimulationStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal["simulate"]
    run_id: UUID
    scenario: WhatIfRequest


WorkflowStart = Annotated[PlanStart | SimulationStart, Field(discriminator="intent")]


class WorkflowTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["approve", "reject", "pause", "resume", "cancel"]
    revision: int = Field(ge=0)


class UndoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=0)
    confirm: Literal[True]


class TraceEvent(BaseModel):
    agent: str
    outcome: str
    at: datetime


class StoredPlanTask(BaseModel):
    title: str
    description: str | None
    priority: Literal["low", "medium", "high"]
    estimated_minutes: int
    deadline: datetime | None
    position: int


class StoredPlan(BaseModel):
    goal_id: int
    goal_title: str
    generation_mode: Literal["rule_based", "openrouter"]
    tasks: list[StoredPlanTask]


class WorkflowEvidence(BaseModel):
    source: Literal["aura.goal"]
    context: ContextPreview | None = None
    grant_id: UUID | None = None
    reconciled: bool = False
    status: Literal["verified"] | None = None
    task_ids: list[int] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    plan: StoredPlan | None = None
    schedule: SchedulePreviewResponse | None = None
    capacity: CapacityFinding | None = None
    comparison: PlanComparison | None = None
    simulation: WhatIfResponse | None = None
    trace: list[TraceEvent] = Field(default_factory=list)
    approval_status: str | None = None
    evidence: WorkflowEvidence | None = None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_id: int | None
    status: Literal["awaiting_approval", "paused", "cancelled", "rejected", "completed", "undone"]
    revision: int
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    result: WorkflowResult
