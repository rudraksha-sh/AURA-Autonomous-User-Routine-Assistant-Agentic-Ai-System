"""Store each user's preferred application theme.

Revision ID: c31d8f2b7a40
Revises: a8c1d7e4029f
"""
from alembic import op
import sqlalchemy as sa

revision = "c31d8f2b7a40"
down_revision = "a8c1d7e4029f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("theme_preference", sa.String(length=10), server_default="system", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "theme_preference")
