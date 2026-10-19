from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    due_soon_reminders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    overdue_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    weekly_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    reminder_lead_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60, server_default="60")
