"""add review plans

Revision ID: 5e7a1d3c9b20
Revises: 8c2d6f49a1b7
Create Date: 2026-07-15 16:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "5e7a1d3c9b20"
down_revision = "8c2d6f49a1b7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "review_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("interval_index", sa.Integer(), nullable=False),
        sa.Column("next_review_at", sa.DateTime(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "topic", name="uq_review_plan_client_topic"),
    )
    with op.batch_alter_table("review_plans", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_review_plans_client_id"), ["client_id"], unique=False)


def downgrade():
    with op.batch_alter_table("review_plans", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_review_plans_client_id"))
    op.drop_table("review_plans")
