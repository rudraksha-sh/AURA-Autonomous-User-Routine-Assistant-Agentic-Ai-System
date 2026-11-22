from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ConstraintVersion = Literal["goal-plan-v1"]



class PlanComparison(BaseModel):
    previous_run_id: UUID
    previous_task_count: int
    proposed_task_count: int
    estimated_minutes_change: int
    overdue_task_count: int
