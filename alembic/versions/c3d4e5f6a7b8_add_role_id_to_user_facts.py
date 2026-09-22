"""Add role_id to user_facts for role-scoped memory

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-21
"""
import sqlalchemy as sa

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_facts") as batch_op:
        batch_op.add_column(sa.Column("role_id", sa.String(length=64), nullable=True))
        batch_op.create_index("idx_user_facts_role", ["role_id", "is_active"])


def downgrade() -> None:
    with op.batch_alter_table("user_facts") as batch_op:
        batch_op.drop_index("idx_user_facts_role")
        batch_op.drop_column("role_id")
