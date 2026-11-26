"""Add explicit planning memory."""
import sqlalchemy as sa
from alembic import op

revision = "67d102ab49c5"
down_revision = "53c42be41d70"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "planning_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("use_for_planning", sa.Boolean, nullable=False),
        sa.Column("version", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_planning_memories_user_id", "planning_memories", ["user_id"])


def downgrade():
    op.drop_table("planning_memories")
