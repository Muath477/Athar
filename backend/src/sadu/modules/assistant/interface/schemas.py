from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from sadu.modules.assistant import api as assistant


class ConversationIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class AnalyseIn(BaseModel):
    facade_id: UUID | None = None


class AttachmentOut(BaseModel):
    id: str
    kind: str
    file_name: str
    media_type: str
    size_bytes: int
    url: str


class ActionOut(BaseModel):
    id: str
    kind: str
    status: str
    file_name: str
    note_ar: str
    decided_at: datetime | None


class MessageOut(BaseModel):
    id: str
    role: str
    text: str
    skill: str | None
    skill_title: str | None
    tool: str | None
    data: dict[str, Any]
    created_at: datetime
    attachments: list[AttachmentOut]
    action: ActionOut | None


class ConversationSummaryOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationOut(ConversationSummaryOut):
    messages: list[MessageOut]


def summary_out(summary: assistant.ConversationSummary) -> ConversationSummaryOut:
    return ConversationSummaryOut(
        id=str(summary.id), title=summary.title, created_at=summary.created_at, updated_at=summary.updated_at
    )


def conversation_out(view: assistant.ConversationView, skill_titles: Mapping[str, str]) -> ConversationOut:
    return ConversationOut(
        **summary_out(view.summary).model_dump(),
        messages=[message_out(m, skill_titles) for m in view.messages],
    )


def message_out(message: assistant.MessageView, skill_titles: Mapping[str, str]) -> MessageOut:
    return MessageOut(
        id=str(message.id),
        role=message.role.value,
        text=message.text,
        skill=message.skill,
        skill_title=skill_titles.get(message.skill) if message.skill else None,
        tool=message.tool,
        data=message.data,
        created_at=message.created_at,
        attachments=[attachment_out(a) for a in message.attachments],
        action=action_out(message.action) if message.action else None,
    )


def attachment_out(attachment: assistant.AttachmentView) -> AttachmentOut:
    return AttachmentOut(
        id=str(attachment.id),
        kind=attachment.kind.value,
        file_name=attachment.file_name,
        media_type=attachment.media_type,
        size_bytes=attachment.size_bytes,
        url=assistant.attachment_path(attachment.id),
    )


def action_out(action: assistant.ActionView) -> ActionOut:
    return ActionOut(
        id=str(action.id),
        kind=action.kind.value,
        status=action.status.value,
        file_name=str(action.payload.get("file_name", "")),
        note_ar=str(action.payload.get("note_ar", "")),
        decided_at=action.decided_at,
    )
