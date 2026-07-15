"""add profile memory controls

Revision ID: 8c2d6f49a1b7
Revises: 393fb1e6ddaf
Create Date: 2026-07-15 15:10:00

"""
from alembic import op
import sqlalchemy as sa


revision = "8c2d6f49a1b7"
down_revision = "393fb1e6ddaf"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("learner_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("memory_enabled", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(sa.Column("memory_reset_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("memory_updated_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("learner_profiles", schema=None) as batch_op:
        batch_op.alter_column("memory_enabled", server_default=None)


def downgrade():
    with op.batch_alter_table("learner_profiles", schema=None) as batch_op:
        batch_op.drop_column("memory_updated_at")
        batch_op.drop_column("memory_reset_at")
        batch_op.drop_column("memory_enabled")
