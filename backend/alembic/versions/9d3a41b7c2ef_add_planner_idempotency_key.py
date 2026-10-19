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
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=36), nullable=True))
        batch_op.create_unique_constraint("uq_agent_runs_user_idempotency", ["user_id", "idempotency_key"])


def downgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.drop_constraint("uq_agent_runs_user_idempotency", type_="unique")
        batch_op.drop_column("idempotency_key")
