from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_agent_runs_user_idempotency"),)

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    goal_id: Mapped[int | None] = mapped_column(
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    agent_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    input: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    output: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    idempotency_key: Mapped[str | None] = mapped_column(String(36), nullable=True)

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
