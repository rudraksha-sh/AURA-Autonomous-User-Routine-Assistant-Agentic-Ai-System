from typing import Literal

from pydantic import BaseModel, ConfigDict


class NotificationPreferences(BaseModel):
    due_soon_reminders: bool = True
    overdue_alerts: bool = True
    weekly_summary: bool = False
    reminder_lead_time_minutes: Literal[15, 30, 60, 1440] = 60

    model_config = ConfigDict(from_attributes=True)
