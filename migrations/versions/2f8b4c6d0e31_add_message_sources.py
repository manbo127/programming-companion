"""add cited sources to messages

Revision ID: 2f8b4c6d0e31
Revises: 5e7a1d3c9b20
Create Date: 2026-07-15 17:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "2f8b4c6d0e31"
down_revision = "5e7a1d3c9b20"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sources_json", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_column("sources_json")
