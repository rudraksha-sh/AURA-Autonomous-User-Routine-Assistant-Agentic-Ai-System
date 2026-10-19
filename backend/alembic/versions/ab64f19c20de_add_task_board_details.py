"""add task board notes, subtasks, and activity history

Revision ID: ab64f19c20de
Revises: c31d8f2b7a40
Create Date: 2026-10-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ab64f19c20de"
down_revision: Union[str, Sequence[str], None] = "c31d8f2b7a40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("notes", sa.Text(), nullable=True))
    op.create_table(
        "task_subtasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_subtasks_id"), "task_subtasks", ["id"], unique=False)
    op.create_index(op.f("ix_task_subtasks_task_id"), "task_subtasks", ["task_id"], unique=False)
    op.create_table(
        "task_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_activities_id"), "task_activities", ["id"], unique=False)
    op.create_index(op.f("ix_task_activities_task_id"), "task_activities", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_task_activities_task_id"), table_name="task_activities")
    op.drop_index(op.f("ix_task_activities_id"), table_name="task_activities")
    op.drop_table("task_activities")
    op.drop_index(op.f("ix_task_subtasks_task_id"), table_name="task_subtasks")
    op.drop_index(op.f("ix_task_subtasks_id"), table_name="task_subtasks")
    op.drop_table("task_subtasks")
    op.drop_column("tasks", "notes")
