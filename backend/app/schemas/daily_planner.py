from datetime import date, datetime, time, timezone
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PlanningPreferencesInput(BaseModel):
    timezone_name: str = Field(default="UTC", min_length=1, max_length=64)
    workday_start: time = time(9, 0)
    workday_end: time = time(17, 0)
    preferred_session_minutes: int = Field(default=50, ge=15, le=180)
    break_minutes: int = Field(default=10, ge=0, le=60)
    daily_capacity_minutes: int = Field(default=360, ge=30, le=720)

    @field_validator("timezone_name")
    @classmethod
    def timezone_must_exist(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Use a valid IANA time zone, such as Europe/London") from exc
        return value

    @model_validator(mode="after")
    def constraints_must_fit_workday(self):
        if self.workday_start >= self.workday_end:
            raise ValueError("Workday end must be later than workday start")
        available = int((datetime.combine(date.min, self.workday_end) - datetime.combine(date.min, self.workday_start)).total_seconds() // 60)
        if self.daily_capacity_minutes > available:
            raise ValueError("Daily capacity cannot exceed the configured workday")
        return self

    model_config = ConfigDict(from_attributes=True)


class PlanningPreferencesResponse(PlanningPreferencesInput):
    pass


class SchedulePreviewRequest(BaseModel):
    target_date: date


class WhatIfTaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    estimated_minutes: int = Field(ge=1, le=480)
    priority: Literal["low", "medium", "high"] = "high"
    deadline: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task title cannot be blank")
        return value


class WhatIfRequest(BaseModel):
    target_date: date
    capacity_minutes: int | None = Field(default=None, ge=30, le=720)
    proposed_task: WhatIfTaskInput | None = None
    unavailable_start_at: datetime | None = None
    unavailable_minutes: int | None = Field(default=None, ge=1, le=240)

    @model_validator(mode="after")
    def scenario_must_change_something(self):
        if self.capacity_minutes is None and self.proposed_task is None and self.unavailable_start_at is None:
            raise ValueError("Provide a capacity change, proposed task, or unavailable time slot")
        if (self.unavailable_start_at is None) != (self.unavailable_minutes is None):
            raise ValueError("Unavailable start time and duration must be provided together")
        if self.unavailable_start_at is not None and (self.unavailable_start_at.tzinfo is None or self.unavailable_start_at.utcoffset() is None):
            raise ValueError("Unavailable time must include a time zone")
        return self


class WhatIfEntry(BaseModel):
    task_id: int | None
    title: str
    priority: Literal["low", "medium", "high"]
    segment_index: int
    start_at: datetime
    end_at: datetime
    duration_minutes: int = Field(ge=1)
    explanation: str
    is_proposed_task: bool = False


class WhatIfUnscheduledTask(BaseModel):
    task_id: int | None
    title: str
    remaining_minutes: int | None
    reason: str
    is_proposed_task: bool = False


class WhatIfSchedule(BaseModel):
    target_date: date
    timezone_name: str
    capacity_minutes: int
    scheduled_minutes: int
    entries: list[WhatIfEntry]
    unscheduled: list[WhatIfUnscheduledTask]


class WhatIfResponse(BaseModel):
    baseline: WhatIfSchedule
    simulated: WhatIfSchedule
    tasks_no_longer_fit: list[str]
    potential_deadline_conflicts: list[str]
    explanations: list[str]


class ScheduledTaskProposal(BaseModel):
    task_id: int
    title: str
    priority: Literal["low", "medium", "high"]
    segment_index: int
    start_at: datetime
    end_at: datetime
    duration_minutes: int = Field(ge=1)
    explanation: str


class UnscheduledTask(BaseModel):
    task_id: int
    title: str
    remaining_minutes: int | None
    reason: str


class SchedulePreviewResponse(BaseModel):
    target_date: date
    timezone_name: str
    capacity_minutes: int
    scheduled_minutes: int
    entries: list[ScheduledTaskProposal]
    unscheduled: list[UnscheduledTask]


class ScheduleSaveEntry(BaseModel):
    task_id: int
    start_at: datetime
    duration_minutes: int = Field(ge=1, le=180)

    @field_validator("start_at")
    @classmethod
    def start_time_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Schedule entry times must include a time zone")
        return value


class ScheduleSaveRequest(BaseModel):
    idempotency_key: UUID
    target_date: date
    entries: list[ScheduleSaveEntry] = Field(min_length=1, max_length=40)


class ScheduleEntryResponse(ScheduledTaskProposal):
    id: int


class DailyScheduleResponse(BaseModel):
    id: int
    target_date: date
    timezone_name: str
    status: str
    capacity_minutes: int
    created_at: datetime
    entries: list[ScheduleEntryResponse]


class ScheduleReadResponse(BaseModel):
    schedule: DailyScheduleResponse | None
