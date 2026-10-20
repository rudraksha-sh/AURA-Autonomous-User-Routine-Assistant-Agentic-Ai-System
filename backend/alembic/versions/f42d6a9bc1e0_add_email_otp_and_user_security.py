"""Add OTP codes and account security flags.

Revision ID: f42d6a9bc1e0
Revises: a61d9b572cf0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f42d6a9bc1e0"
down_revision: Union[str, Sequence[str], None] = "a61d9b572cf0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Keep every account that existed before email verification able to log in.
    op.execute(sa.text("UPDATE users SET email_verified = TRUE"))
    op.add_column("users", sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("purpose IN ('verify_email', 'reset_password', 'login_2fa', 'enable_2fa', 'disable_2fa')", name="ck_otp_codes_purpose"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_otp_codes_user_purpose", "otp_codes", ["user_id", "purpose"])


def downgrade() -> None:
    op.drop_index("ix_otp_codes_user_purpose", table_name="otp_codes")
    op.drop_table("otp_codes")
    op.drop_column("users", "token_version")
    op.drop_column("users", "two_factor_enabled")
    op.drop_column("users", "email_verified")

