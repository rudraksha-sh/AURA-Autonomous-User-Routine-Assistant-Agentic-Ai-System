"""Add autonomous planning preference to goals."""

from alembic import op
import sqlalchemy as sa


revision = "cfa02bf11def"
down_revision = "f42d6a9bc1e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "goals",
        sa.Column(
            "continue_without_asking",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("goals", "continue_without_asking")
