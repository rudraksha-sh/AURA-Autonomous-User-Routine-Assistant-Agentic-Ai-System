"""add preferences and persisted daily schedules

Revision ID: 37b8514f09c1
Revises: 9d3a41b7c2ef
Create Date: 2026-10-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "37b8514f09c1"
down_revision: Union[str, Sequence[str], None] = "9d3a41b7c2ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_planning_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("timezone_name", sa.String(length=64), nullable=False),
        sa.Column("workday_start", sa.Time(), nullable=False),
        sa.Column("workday_end", sa.Time(), nullable=False),
        sa.Column("preferred_session_minutes", sa.Integer(), nullable=False),
        sa.Column("break_minutes", sa.Integer(), nullable=False),
        sa.Column("daily_capacity_minutes", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("workday_start < workday_end", name="ck_planning_workday_order"),
        sa.CheckConstraint("preferred_session_minutes > 0", name="ck_planning_session_positive"),
        sa.CheckConstraint("break_minutes >= 0", name="ck_planning_break_nonnegative"),
        sa.CheckConstraint("daily_capacity_minutes > 0", name="ck_planning_capacity_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "daily_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("timezone_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("capacity_minutes", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_daily_schedule_user_idempotency"),
    )
    op.create_index("ix_daily_schedules_id", "daily_schedules", ["id"], unique=False)
    op.create_index("ix_daily_schedules_user_id", "daily_schedules", ["user_id"], unique=False)
    op.create_index("ix_daily_schedules_target_date", "daily_schedules", ["target_date"], unique=False)
    op.create_table(
        "schedule_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.String(length=255), nullable=False),
        sa.CheckConstraint("duration_minutes > 0", name="ck_schedule_entry_duration_positive"),
        sa.ForeignKeyConstraint(["schedule_id"], ["daily_schedules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schedule_id", "task_id", "segment_index", name="uq_schedule_task_segment"),
    )
    op.create_index("ix_schedule_entries_id", "schedule_entries", ["id"], unique=False)
    op.create_index("ix_schedule_entries_schedule_id", "schedule_entries", ["schedule_id"], unique=False)
    op.create_index("ix_schedule_entries_task_id", "schedule_entries", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_schedule_entries_task_id", table_name="schedule_entries")
    op.drop_index("ix_schedule_entries_schedule_id", table_name="schedule_entries")
    op.drop_index("ix_schedule_entries_id", table_name="schedule_entries")
    op.drop_table("schedule_entries")
    op.drop_index("ix_daily_schedules_target_date", table_name="daily_schedules")
    op.drop_index("ix_daily_schedules_user_id", table_name="daily_schedules")
    op.drop_index("ix_daily_schedules_id", table_name="daily_schedules")
    op.drop_table("daily_schedules")
    op.drop_table("user_planning_preferences")
