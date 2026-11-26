from pydantic import BaseModel, Field


class CapacityFinding(BaseModel):
    remaining_minutes: int = Field(ge=0)
    fits_proposed_day: bool
    workload_minutes: int | None = Field(default=None, ge=0)
    workload_pressure_pct: int | None = Field(default=None, ge=0)
    schedule_feasibility_pct: int | None = Field(default=None, ge=0, le=100)
    deadline_risk_tasks: int = Field(default=0, ge=0)
    calendar_conflicts: int = Field(default=0, ge=0)
    reasons: list[str] = Field(default_factory=list)
