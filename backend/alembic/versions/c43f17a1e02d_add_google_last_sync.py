"""Track the last successful Google calendar sync.

Revision ID: c43f17a1e02d
Revises: d7e5a2c98410
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c43f17a1e02d"
down_revision: Union[str, Sequence[str], None] = "d7e5a2c98410"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("integrations", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("integrations", "last_synced_at")
