from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk, utc_now


class ConversationRow(UuidPk, Timestamped, Base):
    __tablename__ = "assistant_conversations"
    __table_args__ = (Index("ix_assistant_conversations_owner_recent", "owner_id", text("updated_at DESC")),)

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    replying_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MessageRow(UuidPk, Timestamped, Base):
    __tablename__ = "assistant_messages"
    __table_args__ = (Index("ix_assistant_messages_conversation_order", "conversation_id", "created_at"),)

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(8))
    text: Mapped[str] = mapped_column(Text)
    skill: Mapped[str | None] = mapped_column(String(64))
    tool: Mapped[str | None] = mapped_column(String(32))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class AttachmentRow(UuidPk, Timestamped, Base):
    __tablename__ = "assistant_attachments"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("assistant_messages.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    file_name: Mapped[str] = mapped_column(String(200))
    media_type: Mapped[str] = mapped_column(String(64))
    object_key: Mapped[str] = mapped_column(String(300))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    faces_blurred: Mapped[int] = mapped_column(Integer, default=0)


class PendingActionRow(UuidPk, Timestamped, Base):
    __tablename__ = "assistant_pending_actions"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("assistant_messages.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(12))
    decided_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
