"""add revocable account sessions

Revision ID: 4d6f8b0c2e19
Revises: 3c5e7a9b1d08
Create Date: 2026-07-15 19:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = "4d6f8b0c2e19"
down_revision = "3c5e7a9b1d08"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "account_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("account_sessions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_account_sessions_client_id"), ["client_id"], unique=False)


def downgrade():
    with op.batch_alter_table("account_sessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_account_sessions_client_id"))
    op.drop_table("account_sessions")
