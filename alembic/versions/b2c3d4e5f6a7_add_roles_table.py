"""Add roles table and chat_threads.role_id

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-21
"""
import sqlalchemy as sa

from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "c2d68761ce0f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- roles table ----
    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("collection_name", sa.String(length=128), nullable=True),
        sa.Column(
            "citations_enabled", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("model_override", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
    )
    op.create_index("idx_roles_active", "roles", ["is_active"])

    # ---- chat_threads.role_id (nullable, no FK constraint for flexibility) ----
    with op.batch_alter_table("chat_threads") as batch_op:
        batch_op.add_column(sa.Column("role_id", sa.String(length=64), nullable=True))

    # ---- Seed a default role ----
    op.execute(
        """
        INSERT OR IGNORE INTO roles
            (id, name, system_prompt, collection_name, citations_enabled, model_override, is_active)
        VALUES (
            'default',
            'Default',
            'You are MAi-RAG-PA, a helpful, privacy-first AI assistant. Answer directly and accurately.',
            NULL,
            1,
            NULL,
            1
        )
    """
    )


def downgrade() -> None:
    with op.batch_alter_table("chat_threads") as batch_op:
        batch_op.drop_column("role_id")
    op.drop_index("idx_roles_active", table_name="roles")
    op.drop_table("roles")
