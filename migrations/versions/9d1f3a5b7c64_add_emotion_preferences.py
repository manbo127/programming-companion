"""add emotion score and feedback preference

Revision ID: 9d1f3a5b7c64
Revises: 7a9c1e3f5b42
Create Date: 2026-07-15 18:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "9d1f3a5b7c64"
down_revision = "7a9c1e3f5b42"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("learner_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("feedback_style", sa.String(length=20), nullable=False, server_default="balanced")
        )
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("emotion_score", sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_column("emotion_score")
    with op.batch_alter_table("learner_profiles", schema=None) as batch_op:
        batch_op.drop_column("feedback_style")
