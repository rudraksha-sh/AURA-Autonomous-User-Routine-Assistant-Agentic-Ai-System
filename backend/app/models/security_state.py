"""Shared security budgets and expiring OAuth grants."""
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Table

from app.db.session import Base


rate_buckets = Table(
    "security_rate_buckets", Base.metadata,
    Column("policy", String(64), primary_key=True),
    Column("principal_digest", String(64), primary_key=True),
    Column("hits", JSON, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Index("ix_security_rate_buckets_expiry", "policy", "expires_at"),
)

oauth_states = Table(
    "security_oauth_states", Base.metadata,
    Column("state_digest", String(64), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("scopes", JSON, nullable=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Index("ix_security_oauth_states_expiry", "expires_at"),
    Index("ix_security_oauth_states_user", "user_id"),
)
