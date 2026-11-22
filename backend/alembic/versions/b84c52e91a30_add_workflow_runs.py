"""Add tenant-owned workflow runs and checkpoint journals."""

import sqlalchemy as sa
from alembic import op

revision = "b84c52e91a30"
down_revision = "cfa02bf11def"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_id", sa.Integer, sa.ForeignKey("goals.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("checkpoint", sa.JSON, nullable=False),
        sa.Column("result", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_runs_user_id", "workflow_runs", ["user_id"])

    op.create_table(
        "autonomy_grants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_id", sa.Integer, sa.ForeignKey("goals.id", ondelete="SET NULL")),
        sa.Column("operation", sa.String(40), nullable=False),
        sa.Column("consent_version", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("runs_remaining", sa.Integer, nullable=False),
        sa.Column("task_limit", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("runs_remaining >= 0 AND runs_remaining <= 5", name="ck_autonomy_remaining"),
        sa.CheckConstraint("task_limit BETWEEN 3 AND 8", name="ck_autonomy_task_limit"),
        sa.CheckConstraint("status IN ('active','paused','revoked')", name="ck_autonomy_status"),
    )
    op.create_index("ix_autonomy_grants_user_id", "autonomy_grants", ["user_id"])


def downgrade():
    op.drop_table("autonomy_grants")
    op.drop_table("workflow_runs")
