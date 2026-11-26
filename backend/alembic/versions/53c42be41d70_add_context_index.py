"""Create the authorized context index.

Revision ID: 53c42be41d70
Revises: b84c52e91a30
"""
import sqlalchemy as sa
from alembic import op

from app.models.context import Vector384, create_invalidation_v1, drop_invalidation_v1

revision = "53c42be41d70"
down_revision = "b84c52e91a30"
branch_labels = None
depends_on = None


def upgrade():
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "context_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_id", sa.Integer, sa.ForeignKey("goals.id", ondelete="CASCADE")),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("tasks.id", ondelete="CASCADE")),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("version", sa.String(36), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("stale", sa.Boolean, nullable=False),
        sa.UniqueConstraint("user_id", "source_key"),
    )
    for column in ("user_id", "goal_id", "task_id"):
        op.create_index(f"ix_context_sources_{column}", "context_sources", [column])
    op.create_table(
        "context_chunks",
        sa.Column("source_id", sa.String(36), sa.ForeignKey("context_sources.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("ordinal", sa.Integer, primary_key=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", sa.Text().with_variant(Vector384(), "postgresql"), nullable=False),
    )
    for statement in create_invalidation_v1(dialect):
        op.execute(statement)


def downgrade():
    for statement in drop_invalidation_v1(op.get_bind().dialect.name):
        op.execute(statement)
    op.drop_table("context_chunks")
    op.drop_table("context_sources")
