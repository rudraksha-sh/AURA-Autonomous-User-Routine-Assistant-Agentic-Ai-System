from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ExternalAction(Base):
    """A single-resource, single-effect consent checkpoint and outbox record."""

    __tablename__ = "external_actions"
    __table_args__ = (UniqueConstraint("user_id", "request_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    request_id: Mapped[str] = mapped_column(String(36))
    provider: Mapped[str] = mapped_column(String(32))
    operation: Mapped[str] = mapped_column(String(40))
    goal_version: Mapped[str] = mapped_column(String(64))
    fingerprint: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(16))
    consent: Mapped[str] = mapped_column(String(16))
    revision: Mapped[int]
    attempts: Mapped[int]
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    receipt: Mapped[dict | None] = mapped_column(JSON)
    audit: Mapped[list] = mapped_column(JSON)
