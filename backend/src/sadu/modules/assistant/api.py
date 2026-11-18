import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import anyio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.admin import api as admin
from sadu.modules.assistant.application.agent import Agent
from sadu.modules.assistant.application.context import (
    AttachmentRef,
    HistoryEntry,
    ToolOutcome,
    TurnContext,
)
from sadu.modules.assistant.application.events import (
    Replied,
    SkillChosen,
    Thinking,
    ToolFinished,
    ToolStarted,
)
from sadu.modules.assistant.application.ports import ReportNotice, SpecialistChannel
from sadu.modules.assistant.application.tools import Toolbox, ToolDeps
from sadu.modules.assistant.domain.conversation import (
    MAX_ATTACHMENTS_PER_MESSAGE,
    MAX_DOCUMENT_BYTES,
    ActionAlreadySettled,
    ActionKind,
    ActionStatus,
    AttachmentKind,
    MessageRole,
    is_pdf,
    safe_file_name,
    settle,
    title_from,
)
from sadu.modules.assistant.domain.decision import ToolCall, ToolName
from sadu.modules.assistant.domain.skills import Skill
from sadu.modules.assistant.infrastructure.notifier import NoSpecialistChannel, WebhookSpecialistChannel
from sadu.modules.assistant.infrastructure.orm import (
    AttachmentRow,
    ConversationRow,
    MessageRow,
    PendingActionRow,
)
from sadu.modules.assistant.infrastructure.scripted_planner import ScriptedPlanner
from sadu.modules.assistant.infrastructure.skill_files import load_skills
from sadu.modules.capture import api as capture
from sadu.modules.mapping import api as mapping
from sadu.shared.config import Settings
from sadu.shared.errors import Conflict, NotFound, SaduError
from sadu.shared.ports.llm import LLMPort
from sadu.shared.storage import ObjectStore, new_object_key
from sadu.shared.web import API_PREFIX, UnitOfWork

__all__ = [
    "ActionStatus",
    "AttachmentKind",
    "MessageRole",
    "ScriptedPlanner",
    "SkillChosen",
    "Thinking",
    "ToolName",
    "ToolStarted",
    "load_skills",
]

REPLY_LEASE = timedelta(minutes=3)
CONVERSATIONS_LISTED = 50
NEW_CONVERSATION_TITLE = "محادثة جديدة"
UNNAMED_PHOTO = "صورة.jpg"
UNNAMED_DOCUMENT = "مستند.pdf"


@dataclass(frozen=True)
class Dependencies:
    unit_of_work: UnitOfWork
    store: ObjectStore
    llm: LLMPort
    detector: mapping.DamageDetector
    channel: SpecialistChannel
    catalog_path: Path
    map_rows: int
    public_origin: str


@dataclass(frozen=True)
class Upload:
    file_name: str | None
    data: bytes


@dataclass(frozen=True)
class AttachmentView:
    id: UUID
    kind: AttachmentKind
    file_name: str
    media_type: str
    size_bytes: int
    object_key: str


@dataclass(frozen=True)
class ActionView:
    id: UUID
    kind: ActionKind
    status: ActionStatus
    payload: dict[str, Any]
    decided_at: datetime | None


@dataclass(frozen=True)
class MessageView:
    id: UUID
    role: MessageRole
    text: str
    skill: str | None
    tool: str | None
    data: dict[str, Any]
    created_at: datetime
    attachments: tuple[AttachmentView, ...] = ()
    action: ActionView | None = None


@dataclass(frozen=True)
class ConversationSummary:
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ConversationView:
    summary: ConversationSummary
    messages: tuple[MessageView, ...]


@dataclass(frozen=True)
class MessageSaved:
    message: MessageView
    final: bool


type ReplyEvent = SkillChosen | Thinking | ToolStarted | MessageSaved


def build_assistant(
    settings: Settings,
    *,
    llm: LLMPort,
    detector: mapping.DamageDetector,
    unit_of_work: UnitOfWork,
    store: ObjectStore,
) -> "Assistant":
    skills = load_skills()
    use_script = settings.sadu_demo_mode and settings.anthropic_api_key is None
    channel: SpecialistChannel = (
        WebhookSpecialistChannel(settings.sadu_specialist_webhook_url)
        if settings.sadu_specialist_webhook_url
        else NoSpecialistChannel()
    )
    deps = Dependencies(
        unit_of_work=unit_of_work,
        store=store,
        llm=ScriptedPlanner(skills) if use_script else llm,
        detector=detector,
        channel=channel,
        catalog_path=settings.treatment_catalog_path,
        map_rows=settings.sadu_map_rows,
        public_origin=settings.sadu_public_origin,
    )
    return Assistant(deps, skills)


class Assistant:
    def __init__(self, deps: Dependencies, skills: Sequence[Skill]) -> None:
        self._deps = deps
        self._toolbox = Toolbox(
            ToolDeps(deps.unit_of_work, deps.store, deps.detector, deps.catalog_path, deps.map_rows)
        )
        self._agent = Agent(deps.llm, skills, self._toolbox)

    @property
    def skills(self) -> tuple[Skill, ...]:
        return self._agent.skills

    async def reply(
        self, conversation_id: UUID, user: admin.UserView, request_id: str | None
    ) -> AsyncIterator[ReplyEvent]:
        async with self._deps.unit_of_work() as session:
            context = await _start_turn(session, conversation_id, user, request_id)
        return self._turn(context)

    async def _turn(self, context: TurnContext) -> AsyncIterator[ReplyEvent]:
        try:
            async for event in self._agent.run(context):
                if isinstance(event, ToolFinished):
                    async with self._deps.unit_of_work() as session:
                        saved = await _save_outcome(session, context.conversation_id, event.outcome)
                    yield MessageSaved(saved, final=False)
                elif isinstance(event, Replied):
                    async with self._deps.unit_of_work() as session:
                        saved = await _save_reply(session, context.conversation_id, event)
                    yield MessageSaved(saved, final=True)
                else:
                    yield event
        finally:
            with anyio.CancelScope(shield=True):
                async with self._deps.unit_of_work() as session:
                    await _finish_turn(session, context.conversation_id)

    async def analyse_attachment(
        self,
        conversation_id: UUID,
        attachment_id: UUID,
        *,
        facade_id: UUID | None,
        user: admin.UserView,
        request_id: str | None,
    ) -> MessageView:
        async with self._deps.unit_of_work() as session:
            row = await _owned(session, conversation_id, user.id)
            context = await _context(session, row, user, request_id)
        arguments = {"attachment_id": str(attachment_id), "facade_id": str(facade_id) if facade_id else None}
        outcome = await self._toolbox.run(ToolCall(ToolName.ANALYSE_PHOTO, arguments), context, [])
        async with self._deps.unit_of_work() as session:
            return await _save_outcome(session, conversation_id, outcome)

    async def decide_action(
        self, action_id: UUID, *, confirm: bool, user_id: UUID, request_id: str | None
    ) -> MessageView:
        async with self._deps.unit_of_work() as session:
            action = await session.get(PendingActionRow, action_id, with_for_update=True)
            if action is None:
                raise NotFound("not_found")
            conversation = await _owned(session, action.conversation_id, user_id)
            try:
                status = settle(ActionStatus(action.status), confirm=confirm)
            except ActionAlreadySettled as error:
                raise Conflict("action_already_decided") from error
            action.status, action.decided_by, action.decided_at = status, user_id, datetime.now(UTC)

            payload = action.payload
            delivered = None
            if status is ActionStatus.CONFIRMED:
                delivered = await self._deps.channel.deliver(
                    ReportNotice(
                        file_name=payload["file_name"],
                        link=f"{self._deps.public_origin}{attachment_path(UUID(payload['attachment_id']))}",
                        conversation_title=conversation.title,
                        note_ar=payload.get("note_ar") or "",
                    )
                )
            await admin.audit(
                session,
                actor_id=user_id,
                action="assistant.report_sent"
                if status is ActionStatus.CONFIRMED
                else "assistant.send_cancelled",
                target_type="assistant_attachment",
                target_id=payload["attachment_id"],
                details={
                    "action_id": str(action.id),
                    "conversation_id": str(conversation.id),
                    "channel": self._deps.channel.name,
                    "delivered": delivered,
                },
                request_id=request_id,
            )
            outcome = ToolOutcome(
                ToolName.SEND_REPORT,
                True,
                _decision_text(payload["file_name"], status, delivered=delivered),
                {"action_id": str(action.id), "status": status.value, "delivered": delivered},
            )
            return await _save_outcome(session, conversation.id, outcome)


async def create_conversation(
    session: AsyncSession, owner_id: UUID, title: str | None
) -> ConversationSummary:
    row = ConversationRow(owner_id=owner_id, title=title_from(title or "", NEW_CONVERSATION_TITLE))
    session.add(row)
    await session.flush()
    return _summary(row)


async def list_conversations(session: AsyncSession, owner_id: UUID) -> list[ConversationSummary]:
    rows = await session.scalars(
        select(ConversationRow)
        .where(ConversationRow.owner_id == owner_id)
        .order_by(ConversationRow.updated_at.desc())
        .limit(CONVERSATIONS_LISTED)
    )
    return [_summary(row) for row in rows]


async def get_conversation(session: AsyncSession, conversation_id: UUID, owner_id: UUID) -> ConversationView:
    row = await _owned(session, conversation_id, owner_id)
    messages = await _messages(session, conversation_id)
    attachments: dict[UUID, list[AttachmentView]] = defaultdict(list)
    for attachment in await _attachments(session, conversation_id):
        attachments[attachment.message_id].append(_attachment_view(attachment))
    actions = {
        action.message_id: _action_view(action)
        for action in await session.scalars(
            select(PendingActionRow).where(PendingActionRow.conversation_id == conversation_id)
        )
    }
    return ConversationView(
        _summary(row),
        tuple(_message_view(m, tuple(attachments[m.id]), actions.get(m.id)) for m in messages),
    )


async def add_user_message(
    session: AsyncSession,
    store: ObjectStore,
    conversation_id: UUID,
    owner_id: UUID,
    *,
    text: str,
    uploads: Sequence[Upload],
) -> MessageView:
    text = text.strip()
    if not text and not uploads:
        raise SaduError("empty_message", status=422)
    if len(uploads) > MAX_ATTACHMENTS_PER_MESSAGE:
        raise SaduError("too_many_attachments", status=422, max_files=MAX_ATTACHMENTS_PER_MESSAGE)
    conversation = await _owned(session, conversation_id, owner_id)
    stored = [await _store_upload(store, upload) for upload in uploads]

    message = MessageRow(conversation_id=conversation_id, role=MessageRole.USER, text=text, data={})
    session.add(message)
    await session.flush()
    for attachment in stored:
        attachment.conversation_id, attachment.message_id = conversation_id, message.id
        session.add(attachment)
    if conversation.title == NEW_CONVERSATION_TITLE and text:
        conversation.title = title_from(text, NEW_CONVERSATION_TITLE)
    conversation.updated_at = datetime.now(UTC)
    await session.flush()
    return _message_view(message, tuple(_attachment_view(a) for a in stored))


async def attachment_for(session: AsyncSession, attachment_id: UUID, user: admin.UserView) -> AttachmentView:
    row = await session.get(AttachmentRow, attachment_id)
    if row is None:
        raise NotFound("not_found")
    conversation = await session.get(ConversationRow, row.conversation_id)
    is_owner = conversation is not None and conversation.owner_id == user.id
    is_specialist_copy = row.kind == AttachmentKind.AUDIT_REPORT and user.role.allows(admin.Permission.REVIEW)
    if not (is_owner or is_specialist_copy):
        raise NotFound("not_found")
    return _attachment_view(row)


def attachment_path(attachment_id: UUID) -> str:
    return f"{API_PREFIX}/assistant/attachments/{attachment_id}"


async def _store_upload(store: ObjectStore, upload: Upload) -> AttachmentRow:
    if is_pdf(upload.data[:8]):
        if len(upload.data) > MAX_DOCUMENT_BYTES:
            raise SaduError("upload_too_large", status=413, max_mb=MAX_DOCUMENT_BYTES // (1024 * 1024))
        key = new_object_key("assistant/documents", "pdf")
        await store.put(key, upload.data, "application/pdf")
        return AttachmentRow(
            kind=AttachmentKind.DOCUMENT,
            file_name=safe_file_name(upload.file_name, UNNAMED_DOCUMENT),
            media_type="application/pdf",
            object_key=key,
            size_bytes=len(upload.data),
        )
    photo = await asyncio.to_thread(capture.process_upload, upload.data)
    key = new_object_key("assistant/photos", "jpg")
    await store.put(key, photo.jpeg, "image/jpeg")
    return AttachmentRow(
        kind=AttachmentKind.PHOTO,
        file_name=safe_file_name(upload.file_name, UNNAMED_PHOTO),
        media_type="image/jpeg",
        object_key=key,
        size_bytes=len(photo.jpeg),
        width=photo.width,
        height=photo.height,
        faces_blurred=photo.faces_blurred,
    )


async def _start_turn(
    session: AsyncSession, conversation_id: UUID, user: admin.UserView, request_id: str | None
) -> TurnContext:
    row = await _owned(session, conversation_id, user.id, lock=True)
    now = datetime.now(UTC)
    if row.replying_since is not None and now - row.replying_since < REPLY_LEASE:
        raise Conflict("assistant_busy")
    context = await _context(session, row, user, request_id)
    if not context.message and not context.latest_attachment_ids:
        raise Conflict("nothing_to_answer")
    row.replying_since = now
    return context


async def _finish_turn(session: AsyncSession, conversation_id: UUID) -> None:
    row = await session.get(ConversationRow, conversation_id, with_for_update=True)
    if row is not None:
        row.replying_since = None
        row.updated_at = datetime.now(UTC)


async def _context(
    session: AsyncSession, row: ConversationRow, user: admin.UserView, request_id: str | None
) -> TurnContext:
    messages = await _messages(session, row.id)
    attachments = await _attachments(session, row.id)
    last = messages[-1] if messages and messages[-1].role == MessageRole.USER else None
    earlier = messages[:-1] if last is not None else messages
    return TurnContext(
        conversation_id=row.id,
        user_id=row.owner_id,
        request_id=request_id,
        message=last.text if last is not None else "",
        attachments=tuple(
            AttachmentRef(a.id, AttachmentKind(a.kind), a.file_name, a.object_key, a.width, a.height)
            for a in attachments
        ),
        latest_attachment_ids=tuple(
            a.id for a in attachments if last is not None and a.message_id == last.id
        ),
        history=tuple(_history_entry(m) for m in earlier),
        can_save_maps=user.role.allows(admin.Permission.SURVEY),
    )


async def _save_outcome(session: AsyncSession, conversation_id: UUID, outcome: ToolOutcome) -> MessageView:
    message = MessageRow(
        conversation_id=conversation_id,
        role=MessageRole.TOOL,
        text=outcome.summary_ar,
        tool=outcome.tool.value,
        data={"ok": outcome.ok, **outcome.data},
    )
    session.add(message)
    await session.flush()
    attachments: tuple[AttachmentView, ...] = ()
    if outcome.attachment is not None:
        new = outcome.attachment
        row = AttachmentRow(
            id=new.id,
            conversation_id=conversation_id,
            message_id=message.id,
            kind=new.kind,
            file_name=new.file_name,
            media_type=new.media_type,
            object_key=new.object_key,
            size_bytes=new.size_bytes,
        )
        session.add(row)
        attachments = (_attachment_view(row),)
    action = None
    if outcome.action is not None:
        action_row = PendingActionRow(
            id=outcome.action.id,
            conversation_id=conversation_id,
            message_id=message.id,
            kind=outcome.action.kind,
            payload=outcome.action.payload,
            status=ActionStatus.PENDING,
        )
        session.add(action_row)
        action = _action_view(action_row)
    await session.flush()
    return _message_view(message, attachments, action)


async def _save_reply(session: AsyncSession, conversation_id: UUID, reply: Replied) -> MessageView:
    message = MessageRow(
        conversation_id=conversation_id,
        role=MessageRole.AGENT,
        text=reply.text,
        skill=reply.skill,
        data={"llm_available": reply.llm_available},
    )
    session.add(message)
    await session.flush()
    return _message_view(message)


async def _owned(
    session: AsyncSession, conversation_id: UUID, owner_id: UUID, *, lock: bool = False
) -> ConversationRow:
    row = await session.get(ConversationRow, conversation_id, with_for_update=lock)
    if row is None or row.owner_id != owner_id:
        raise NotFound("not_found")
    return row


async def _messages(session: AsyncSession, conversation_id: UUID) -> list[MessageRow]:
    rows = await session.scalars(
        select(MessageRow)
        .where(MessageRow.conversation_id == conversation_id)
        .order_by(MessageRow.created_at, MessageRow.id)
    )
    return list(rows)


async def _attachments(session: AsyncSession, conversation_id: UUID) -> list[AttachmentRow]:
    rows = await session.scalars(
        select(AttachmentRow)
        .where(AttachmentRow.conversation_id == conversation_id)
        .order_by(AttachmentRow.created_at, AttachmentRow.id)
    )
    return list(rows)


def _decision_text(file_name: str, status: ActionStatus, *, delivered: bool | None) -> str:
    if status is ActionStatus.CANCELLED:
        return f"أُلغي إرسال «{file_name}»."
    if delivered:
        return f"أُرسل «{file_name}» إلى المختصين للمراجعة والاعتماد."
    return f"سُجل طلب إرسال «{file_name}»، لكن قناة المختصين غير مضبوطة أو لم تستجب. شارك الملف معهم يدويًا."


def _history_entry(row: MessageRow) -> HistoryEntry:
    data = dict(row.data or {})
    ok = bool(data.pop("ok", True))
    tool = ToolName(row.tool) if row.tool else None
    return HistoryEntry(MessageRole(row.role), row.text, tool, ok, data)


def _summary(row: ConversationRow) -> ConversationSummary:
    return ConversationSummary(row.id, row.title, row.created_at, row.updated_at)


def _message_view(
    row: MessageRow, attachments: tuple[AttachmentView, ...] = (), action: ActionView | None = None
) -> MessageView:
    return MessageView(
        id=row.id,
        role=MessageRole(row.role),
        text=row.text,
        skill=row.skill,
        tool=row.tool,
        data=row.data or {},
        created_at=row.created_at,
        attachments=attachments,
        action=action,
    )


def _attachment_view(row: AttachmentRow) -> AttachmentView:
    return AttachmentView(
        row.id, AttachmentKind(row.kind), row.file_name, row.media_type, row.size_bytes, row.object_key
    )


def _action_view(row: PendingActionRow) -> ActionView:
    return ActionView(row.id, ActionKind(row.kind), ActionStatus(row.status), row.payload, row.decided_at)
