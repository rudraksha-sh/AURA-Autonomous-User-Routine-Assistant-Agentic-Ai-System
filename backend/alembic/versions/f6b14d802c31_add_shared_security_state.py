"""Add shared rate-limit buckets and one-time OAuth state."""
from alembic import op
import sqlalchemy as sa

revision = "f6b14d802c31"
down_revision = "e781ac36d940"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "security_rate_buckets",
        sa.Column("policy", sa.String(64), primary_key=True),
        sa.Column("principal_digest", sa.String(64), primary_key=True),
        sa.Column("hits", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_security_rate_buckets_expiry", "security_rate_buckets", ["policy", "expires_at"])
    op.create_table(
        "security_oauth_states",
        sa.Column("state_digest", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_security_oauth_states_expiry", "security_oauth_states", ["expires_at"])
    op.create_index("ix_security_oauth_states_user", "security_oauth_states", ["user_id"])


def downgrade():
    op.drop_table("security_oauth_states")
    op.drop_table("security_rate_buckets")
