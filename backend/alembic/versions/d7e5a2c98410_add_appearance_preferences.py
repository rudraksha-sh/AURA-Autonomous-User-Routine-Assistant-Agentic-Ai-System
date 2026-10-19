"""Add persisted per-user appearance options.

Revision ID: d7e5a2c98410
Revises: ab64f19c20de
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e5a2c98410"
down_revision: Union[str, Sequence[str], None] = "ab64f19c20de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("accent_color", sa.String(length=20), nullable=False, server_default="blue"))
    op.add_column("users", sa.Column("density", sa.String(length=20), nullable=False, server_default="comfortable"))
    op.add_column("users", sa.Column("font_size", sa.String(length=20), nullable=False, server_default="medium"))


def downgrade() -> None:
    op.drop_column("users", "font_size")
    op.drop_column("users", "density")
    op.drop_column("users", "accent_color")
