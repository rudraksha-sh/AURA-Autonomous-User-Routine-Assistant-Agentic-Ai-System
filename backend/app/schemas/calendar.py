from datetime import datetime

from pydantic import BaseModel, Field


class CalendarBusyBlock(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    start_at: datetime
    end_at: datetime
    all_day: bool = False


class CalendarBusyResponse(BaseModel):
    calendar_synced: bool
    busy_blocks: list[CalendarBusyBlock]
    message: str | None = None
