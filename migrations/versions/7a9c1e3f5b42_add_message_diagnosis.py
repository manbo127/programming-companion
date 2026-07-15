"""add structured diagnosis to messages

Revision ID: 7a9c1e3f5b42
Revises: 2f8b4c6d0e31
Create Date: 2026-07-15 17:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = "7a9c1e3f5b42"
down_revision = "2f8b4c6d0e31"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("diagnosis_json", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_column("diagnosis_json")
