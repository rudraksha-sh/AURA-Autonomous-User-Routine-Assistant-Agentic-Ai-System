from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.agents.execution.schemas import CreateGoalTasks
from app.schemas.workflow import UtcTimestamp


class GrantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_id: int = Field(gt=0)
    operation: CreateGoalTasks
    consent_version: Literal["local-task-grant-v1"]
    consent: Literal[True]
    duration_minutes: int = Field(ge=5, le=60)
    run_limit: int = Field(ge=1, le=5)
    task_limit: int = Field(ge=3, le=8)


class GrantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_id: int | None
    operation: CreateGoalTasks
    consent_version: str
    status: Literal["active", "paused", "revoked", "expired", "exhausted", "consent_required"]
    runs_remaining: int
    task_limit: int
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    expires_at: UtcTimestamp


class GrantTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["pause", "resume", "revoke"]
