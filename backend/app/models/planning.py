from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class UserPlanningPreference(Base):
    __tablename__ = "user_planning_preferences"
    __table_args__ = (
        CheckConstraint("workday_start < workday_end", name="ck_planning_workday_order"),
        CheckConstraint("preferred_session_minutes > 0", name="ck_planning_session_positive"),
        CheckConstraint("break_minutes >= 0", name="ck_planning_break_nonnegative"),
        CheckConstraint("daily_capacity_minutes > 0", name="ck_planning_capacity_positive"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    timezone_name: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    workday_start: Mapped[time] = mapped_column(Time(), nullable=False, default=time(9, 0))
    workday_end: Mapped[time] = mapped_column(Time(), nullable=False, default=time(17, 0))
    preferred_session_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    break_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    daily_capacity_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=360)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DailySchedule(Base):
    __tablename__ = "daily_schedules"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_daily_schedule_user_idempotency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    timezone_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="approved")
    capacity_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"
    __table_args__ = (
        UniqueConstraint("schedule_id", "task_id", "segment_index", name="uq_schedule_task_segment"),
        CheckConstraint("duration_minutes > 0", name="ck_schedule_entry_duration_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("daily_schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(String(255), nullable=False)
