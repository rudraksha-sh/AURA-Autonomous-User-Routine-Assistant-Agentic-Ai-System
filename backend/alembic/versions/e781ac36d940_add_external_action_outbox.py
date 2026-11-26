"""Add durable external action consent checkpoints and outbox."""
import sqlalchemy as sa
from alembic import op

revision = "e781ac36d940"
down_revision = "67d102ab49c5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "external_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("goals.id", ondelete="SET NULL")),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("operation", sa.String(40), nullable=False),
        sa.Column("goal_version", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("consent", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receipt", sa.JSON()),
        sa.Column("audit", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "request_id"),
    )
    op.create_index("ix_external_actions_user_id", "external_actions", ["user_id"])


def downgrade():
    op.drop_table("external_actions")
