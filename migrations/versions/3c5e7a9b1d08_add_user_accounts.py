"""add optional user accounts

Revision ID: 3c5e7a9b1d08
Revises: 1b3d5f7a9c86
Create Date: 2026-07-15 19:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "3c5e7a9b1d08"
down_revision = "1b3d5f7a9c86"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("clients", schema=None) as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(length=254), nullable=True))
        batch_op.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("locked_until", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f("ix_clients_email"), ["email"], unique=True)


def downgrade():
    with op.batch_alter_table("clients", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_clients_email"))
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_attempts")
        batch_op.drop_column("is_anonymous")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("email")
