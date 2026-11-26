from typing import Literal

from pydantic import BaseModel, Field


class VerificationReceipt(BaseModel):
    status: Literal["verified", "changed", "failed", "unknown"]
    task_ids: list[int]
    changed_task_ids: list[int] = Field(default_factory=list)
    missing_task_ids: list[int] = Field(default_factory=list)
    evidence_version: Literal["task-fingerprint-v1"] | None = None
