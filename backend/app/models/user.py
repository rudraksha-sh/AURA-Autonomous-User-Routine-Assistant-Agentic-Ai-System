from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base



class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user", server_default="user")

    profile_photo_filename: Mapped[str | None] = mapped_column(String(64), nullable=True)

    theme_preference: Mapped[str] = mapped_column(String(10), nullable=False, default="system", server_default="system")

    accent_color: Mapped[str] = mapped_column(String(20), nullable=False, default="blue", server_default="blue")

    density: Mapped[str] = mapped_column(String(20), nullable=False, default="comfortable", server_default="comfortable")

    font_size: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", server_default="medium")

    use_ai_planning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    integrations = relationship(
        "Integration",
        back_populates="user",
        cascade="all, delete-orphan",
    )
