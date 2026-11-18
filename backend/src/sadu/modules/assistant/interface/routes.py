import json
from collections.abc import AsyncIterator
from typing import Annotated, Any
from urllib.parse import quote
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from sse_starlette import EventSourceResponse

from sadu.modules.admin.interface.auth import AssistantUser
from sadu.modules.assistant import api as assistant
from sadu.modules.assistant.domain.conversation import MAX_DOCUMENT_BYTES
from sadu.modules.assistant.interface.schemas import (
    AnalyseIn,
    ConversationIn,
    ConversationOut,
    ConversationSummaryOut,
    MessageOut,
    conversation_out,
    message_out,
    summary_out,
)
from sadu.shared.web import Session, State

log = structlog.get_logger()

router = APIRouter(prefix="/assistant", tags=["assistant"])

MESSAGES_PER_USER_PER_HOUR = 60
REPLIES_PER_USER_PER_HOUR = 30
ANALYSES_PER_USER_PER_HOUR = 30
STREAM_FAILED_AR = "انقطع رد المساعد بسبب خطأ في الخادم. ما حُفظ من خطوات باقٍ في المحادثة؛ أعد المحاولة."


def assistant_service(request: Request) -> assistant.Assistant:
    service: assistant.Assistant = request.app.state.assistant
    return service


Service = Annotated[assistant.Assistant, Depends(assistant_service)]


@router.post("/conversations", status_code=201)
async def create_conversation(body: ConversationIn, user: AssistantUser, session: Session) -> ConversationOut:
    summary = await assistant.create_conversation(session, user.id, body.title)
    return ConversationOut(**summary_out(summary).model_dump(), messages=[])


@router.get("/conversations")
async def list_conversations(user: AssistantUser, session: Session) -> list[ConversationSummaryOut]:
    return [summary_out(s) for s in await assistant.list_conversations(session, user.id)]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID, user: AssistantUser, session: Session, service: Service
) -> ConversationOut:
    view = await assistant.get_conversation(session, conversation_id, user.id)
    return conversation_out(view, _skill_titles(service))


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def post_message(
    conversation_id: UUID,
    user: AssistantUser,
    state: State,
    service: Service,
    text: Annotated[str, Form(max_length=4000)] = "",
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> MessageOut:
    state.rate_limiter.check(f"assistant_messages:{user.id}", MESSAGES_PER_USER_PER_HOUR, 3600)
    uploads = [assistant.Upload(f.filename, await f.read(MAX_DOCUMENT_BYTES + 1)) for f in files or []]
    async with state.unit_of_work() as session:
        message = await assistant.add_user_message(
            session, state.store, conversation_id, user.id, text=text, uploads=uploads
        )
    return message_out(message, _skill_titles(service))


@router.post("/conversations/{conversation_id}/reply")
async def reply(
    conversation_id: UUID, request: Request, user: AssistantUser, state: State, service: Service
) -> EventSourceResponse:
    state.rate_limiter.check(f"assistant_replies:{user.id}", REPLIES_PER_USER_PER_HOUR, 3600)
    events = await service.reply(conversation_id, user, _request_id(request))
    titles = _skill_titles(service)

    async def stream() -> AsyncIterator[dict[str, str]]:
        try:
            async for event in events:
                yield _sse(*_event_payload(event, titles))
        except Exception:
            log.exception("assistant_reply_failed", conversation_id=str(conversation_id))
            yield _sse("error", {"code": "internal_error", "detail_ar": STREAM_FAILED_AR})
            return
        yield _sse("done", {})

    return EventSourceResponse(stream())


@router.post("/conversations/{conversation_id}/attachments/{attachment_id}/analyse")
async def analyse_attachment(
    conversation_id: UUID,
    attachment_id: UUID,
    body: AnalyseIn,
    request: Request,
    user: AssistantUser,
    state: State,
    service: Service,
) -> MessageOut:
    state.rate_limiter.check(f"assistant_analyses:{user.id}", ANALYSES_PER_USER_PER_HOUR, 3600)
    message = await service.analyse_attachment(
        conversation_id,
        attachment_id,
        facade_id=body.facade_id,
        user=user,
        request_id=_request_id(request),
    )
    return message_out(message, _skill_titles(service))


@router.post("/actions/{action_id}/confirm")
async def confirm_action(
    action_id: UUID, request: Request, user: AssistantUser, service: Service
) -> MessageOut:
    message = await service.decide_action(
        action_id, confirm=True, user_id=user.id, request_id=_request_id(request)
    )
    return message_out(message, _skill_titles(service))


@router.post("/actions/{action_id}/cancel")
async def cancel_action(
    action_id: UUID, request: Request, user: AssistantUser, service: Service
) -> MessageOut:
    message = await service.decide_action(
        action_id, confirm=False, user_id=user.id, request_id=_request_id(request)
    )
    return message_out(message, _skill_titles(service))


@router.get("/attachments/{attachment_id}", response_class=Response)
async def attachment_file(
    attachment_id: UUID, user: AssistantUser, session: Session, state: State
) -> Response:
    attachment = await assistant.attachment_for(session, attachment_id, user)
    disposition = "inline" if attachment.kind is assistant.AttachmentKind.PHOTO else "attachment"
    return Response(
        await state.store.get(attachment.object_key),
        media_type=attachment.media_type,
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(attachment.file_name)}",
            "Cache-Control": "private, no-store",
        },
    )


def _event_payload(event: assistant.ReplyEvent, titles: dict[str, str]) -> tuple[str, dict[str, Any]]:
    match event:
        case assistant.SkillChosen(name=name, title_ar=title_ar):
            return "skill", {"name": name, "title_ar": title_ar}
        case assistant.Thinking(step=step):
            return "step", {"step": step}
        case assistant.ToolStarted(tool=tool):
            return "tool_call", {"tool": tool.value}
        case assistant.MessageSaved(message=message, final=final):
            body = message_out(message, titles).model_dump(mode="json")
            return ("message" if final else "tool_result"), {"message": body}


def _sse(name: str, payload: dict[str, Any]) -> dict[str, str]:
    return {"event": name, "data": json.dumps(payload, ensure_ascii=False)}


def _skill_titles(service: assistant.Assistant) -> dict[str, str]:
    return {skill.name: skill.title_ar for skill in service.skills}


def _request_id(request: Request) -> str | None:
    request_id: str | None = getattr(request.state, "request_id", None)
    return request_id
