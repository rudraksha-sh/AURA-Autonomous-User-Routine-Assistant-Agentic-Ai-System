"""Add user roles and private profile photo references.

Revision ID: a8c1d7e4029f
Revises: 37b8514f09c1
"""
from alembic import op
import sqlalchemy as sa

revision = "a8c1d7e4029f"
down_revision = "37b8514f09c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=20), server_default="user", nullable=False))
    op.add_column("users", sa.Column("profile_photo_filename", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_photo_filename")
    op.drop_column("users", "role")
