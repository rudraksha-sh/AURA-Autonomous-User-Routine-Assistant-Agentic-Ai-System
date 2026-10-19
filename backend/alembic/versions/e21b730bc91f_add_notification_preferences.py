"""Add per-user notification preferences.

Revision ID: e21b730bc91f
Revises: c43f17a1e02d
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e21b730bc91f"
down_revision: Union[str, Sequence[str], None] = "c43f17a1e02d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_notification_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("due_soon_reminders", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("overdue_alerts", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("weekly_summary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("reminder_lead_time_minutes", sa.Integer(), server_default="60", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_notification_preferences")
