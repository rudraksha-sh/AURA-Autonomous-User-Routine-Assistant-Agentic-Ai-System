from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AutonomyGrant(Base):
    __tablename__ = "autonomy_grants"
    __table_args__ = (
        CheckConstraint("runs_remaining >= 0 AND runs_remaining <= 5", name="ck_autonomy_remaining"),
        CheckConstraint("task_limit BETWEEN 3 AND 8", name="ck_autonomy_task_limit"),
        CheckConstraint("status IN ('active','paused','revoked')", name="ck_autonomy_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    operation: Mapped[str] = mapped_column(String(40))
    consent_version: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(16))
    runs_remaining: Mapped[int]
    task_limit: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
