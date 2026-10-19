"""Add the per-user AI planning switch.

Revision ID: a61d9b572cf0
Revises: e21b730bc91f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a61d9b572cf0"
down_revision: Union[str, Sequence[str], None] = "e21b730bc91f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("use_ai_planning", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("users", "use_ai_planning")
