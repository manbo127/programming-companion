"""add llm telemetry

Revision ID: 1b3d5f7a9c86
Revises: 9d1f3a5b7c64
Create Date: 2026-07-15 18:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = "1b3d5f7a9c86"
down_revision = "9d1f3a5b7c64"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("llm_model", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("llm_request_id", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("llm_attempts", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("finish_reason", sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_column("finish_reason")
        batch_op.drop_column("llm_attempts")
        batch_op.drop_column("llm_request_id")
        batch_op.drop_column("llm_model")
