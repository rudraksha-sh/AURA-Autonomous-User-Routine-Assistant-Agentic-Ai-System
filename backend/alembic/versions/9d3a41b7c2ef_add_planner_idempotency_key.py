"""add planner save idempotency key

Revision ID: 9d3a41b7c2ef
Revises: f5ac130ca6de
Create Date: 2026-10-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d3a41b7c2ef"
down_revision: Union[str, Sequence[str], None] = "f5ac130ca6de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("idempotency_key", sa.String(length=36), nullable=True))
    op.create_unique_constraint(
        "uq_agent_runs_user_idempotency",
        "agent_runs",
        ["user_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_agent_runs_user_idempotency", "agent_runs", type_="unique")
    op.drop_column("agent_runs", "idempotency_key")
