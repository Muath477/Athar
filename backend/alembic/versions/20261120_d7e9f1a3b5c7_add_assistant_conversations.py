from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7e9f1a3b5c7"
down_revision: str | None = "c4e6a8b0d2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_conversations",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replying_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_assistant_conversations_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assistant_conversations")),
    )
    op.create_index(
        "ix_assistant_conversations_owner_recent",
        "assistant_conversations",
        ["owner_id", sa.literal_column("updated_at DESC")],
        unique=False,
    )
    op.create_table(
        "assistant_messages",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=8), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("skill", sa.String(length=64), nullable=True),
        sa.Column("tool", sa.String(length=32), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["assistant_conversations.id"],
            name=op.f("fk_assistant_messages_conversation_id_assistant_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assistant_messages")),
    )
    op.create_index(
        "ix_assistant_messages_conversation_order",
        "assistant_messages",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "assistant_attachments",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("file_name", sa.String(length=200), nullable=False),
        sa.Column("media_type", sa.String(length=64), nullable=False),
        sa.Column("object_key", sa.String(length=300), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("faces_blurred", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["assistant_conversations.id"],
            name=op.f("fk_assistant_attachments_conversation_id_assistant_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["assistant_messages.id"],
            name=op.f("fk_assistant_attachments_message_id_assistant_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assistant_attachments")),
    )
    op.create_index(
        op.f("ix_assistant_attachments_conversation_id"), "assistant_attachments", ["conversation_id"]
    )
    op.create_index(op.f("ix_assistant_attachments_message_id"), "assistant_attachments", ["message_id"])
    op.create_table(
        "assistant_pending_actions",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["assistant_conversations.id"],
            name=op.f("fk_assistant_pending_actions_conversation_id_assistant_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"],
            ["users.id"],
            name=op.f("fk_assistant_pending_actions_decided_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["assistant_messages.id"],
            name=op.f("fk_assistant_pending_actions_message_id_assistant_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assistant_pending_actions")),
    )
    op.create_index(
        op.f("ix_assistant_pending_actions_conversation_id"), "assistant_pending_actions", ["conversation_id"]
    )
    op.create_index(
        op.f("ix_assistant_pending_actions_message_id"), "assistant_pending_actions", ["message_id"]
    )


def downgrade() -> None:
    op.drop_table("assistant_pending_actions")
    op.drop_table("assistant_attachments")
    op.drop_table("assistant_messages")
    op.drop_index("ix_assistant_conversations_owner_recent", table_name="assistant_conversations")
    op.drop_table("assistant_conversations")
