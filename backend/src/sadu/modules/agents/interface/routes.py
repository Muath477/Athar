import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from pydantic import BaseModel, Field, ValidationError
from sse_starlette import EventSourceResponse

from sadu.modules.admin import api as admin
from sadu.modules.admin.interface.auth import Expert
from sadu.modules.agents import api as agents
from sadu.modules.agents.application.guide import verified_story
from sadu.modules.capture import api as capture
from sadu.modules.capture.api import MAX_UPLOAD_BYTES, CaptureMeta, ObservationStatus
from sadu.modules.passport.interface.auth import OptionalPassport, RequiredPassport
from sadu.modules.stories import api as stories
from sadu.modules.verification import api as verification
from sadu.modules.verification.interface.routes import FindingOut, finding_out
from sadu.shared.errors import Forbidden, SaduError
from sadu.shared.i18n import translate
from sadu.shared.vocabulary import DamageType, Severity
from sadu.shared.web import Session, State, client_ip, limit_per_ip, limit_public_reads, public

router = APIRouter()

FINAL_STATUSES = {ObservationStatus.DONE, ObservationStatus.NEEDS_RETAKE, ObservationStatus.FAILED}
EVENT_POLL_S = 1.0
EVENT_STREAM_MAX_S = 180


class Consent(BaseModel):
    location: bool = False
    heading: bool = False


class ObservationMeta(BaseModel):
    captured_at: datetime
    site_id: UUID | None = None
    mission_id: UUID | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    gps_accuracy_m: float | None = Field(default=None, ge=0)
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    heading_accuracy_deg: float | None = Field(default=None, ge=0)
    consent: Consent = Consent()


class ObservationAccepted(BaseModel):
    observation_id: str
    status: str
    events_url: str


class ObservationOut(BaseModel):
    observation_id: str
    status: str
    detail: dict[str, Any]


class Answer(BaseModel):
    question_id: str = Field(pattern="^which_facade$")
    facade_id: UUID | None


class Review(BaseModel):
    decision: verification.ReviewDecision
    reason: str = Field(min_length=1, max_length=1000)
    damage_type: DamageType | None = None
    severity: Severity | None = None


class SourceOut(BaseModel):
    title: str
    url: str | None
    narrator_name: str | None


class ClaimOut(BaseModel):
    claim_id: str
    text: str
    label: str
    source: SourceOut | None


class StoryOut(BaseModel):
    story_id: str | None
    site_id: str
    facade_id: str | None
    lang: str
    claims: list[ClaimOut]
    message: str | None
    audio_url: str | None
    cached: bool


@router.post(
    "/observations",
    status_code=202,
    tags=["observations"],
    dependencies=[Depends(public), Depends(limit_per_ip("upload", 30, 60))],
)
async def submit_observation(
    request: Request,
    state: State,
    passport_id: OptionalPassport,
    photo: Annotated[UploadFile, File()],
    meta: Annotated[str, Form(max_length=4000)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
) -> ObservationAccepted:
    if passport_id is not None:
        state.rate_limiter.check(f"upload-passport:{passport_id}", 10, 60)
        state.rate_limiter.check(f"upload-passport-day:{passport_id}", 60, 86400)
    try:
        parsed = ObservationMeta.model_validate_json(meta)
    except ValidationError as error:
        raise SaduError("validation_failed", status=422) from error
    raw = await photo.read(MAX_UPLOAD_BYTES + 1)
    capture_meta = CaptureMeta(
        captured_at=parsed.captured_at,
        site_id=parsed.site_id,
        mission_id=parsed.mission_id,
        lat=parsed.lat if parsed.consent.location else None,
        lon=parsed.lon if parsed.consent.location else None,
        gps_accuracy_m=parsed.gps_accuracy_m if parsed.consent.location else None,
        heading_deg=parsed.heading_deg if parsed.consent.heading else None,
        heading_accuracy_deg=parsed.heading_accuracy_deg if parsed.consent.heading else None,
        passport_id=passport_id,
    )
    async with state.unit_of_work() as session:
        observation, created = await capture.create_observation(
            session, state.store, raw_photo=raw, meta=capture_meta, idempotency_key=idempotency_key
        )
    if created:
        state.runner.start(observation.id)
    return ObservationAccepted(
        observation_id=str(observation.id),
        status=observation.status,
        events_url=f"{request.url.path}/{observation.id}/events",
    )


@router.get(
    "/observations/{observation_id}",
    tags=["observations"],
    dependencies=[Depends(public), Depends(limit_public_reads)],
)
async def get_observation(
    observation_id: UUID, session: Session, passport_id: OptionalPassport
) -> ObservationOut:
    observation = await _owned_observation(session, observation_id, passport_id)
    return ObservationOut(
        observation_id=str(observation.id), status=observation.status, detail=observation.status_payload
    )


@router.get(
    "/observations/{observation_id}/events",
    tags=["observations"],
    dependencies=[Depends(public), Depends(limit_per_ip("events", 30, 60))],
)
async def observation_events(
    observation_id: UUID, state: State, passport_id: OptionalPassport
) -> EventSourceResponse:
    async with state.unit_of_work() as session:
        await _owned_observation(session, observation_id, passport_id)

    async def stream() -> AsyncIterator[dict[str, str]]:
        last: tuple[str, str] | None = None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + EVENT_STREAM_MAX_S
        while loop.time() < deadline:
            async with state.unit_of_work() as session:
                observation = await capture.get_observation(session, observation_id)
            current = (observation.status.value, json.dumps(observation.status_payload, sort_keys=True))
            if current != last:
                last = current
                yield {
                    "event": _event_name(observation.status),
                    "data": json.dumps(
                        {"status": observation.status, "detail": observation.status_payload},
                        ensure_ascii=False,
                    ),
                }
            if observation.status in FINAL_STATUSES:
                return
            await asyncio.sleep(EVENT_POLL_S)

    return EventSourceResponse(stream())


@router.post(
    "/observations/{observation_id}/answers",
    status_code=202,
    tags=["observations"],
    dependencies=[Depends(public), Depends(limit_per_ip("answer", 30, 60))],
)
async def answer_question(
    observation_id: UUID, body: Answer, state: State, passport_id: OptionalPassport
) -> ObservationOut:
    async with state.unit_of_work() as session:
        observation = await _owned_observation(session, observation_id, passport_id)
        await state.runner.answer(session, observation_id, body.facade_id)
    return ObservationOut(observation_id=str(observation.id), status="processing", detail={})


@router.get(
    "/sites/{site_id}/story",
    tags=["stories"],
    dependencies=[Depends(public), Depends(limit_per_ip("story", 30, 60))],
)
async def site_story(
    site_id: UUID,
    state: State,
    facade_id: UUID | None = None,
    lang: Annotated[str, Query(pattern="^(ar|en)$")] = "ar",
) -> StoryOut:
    story = await verified_story(state.runner.deps, site_id, facade_id)
    if story is None:
        return StoryOut(
            story_id=None,
            site_id=str(site_id),
            facade_id=str(facade_id) if facade_id else None,
            lang=lang,
            claims=[],
            message=translate("story.no_verified_source", lang),
            audio_url=None,
            cached=False,
        )
    return _story_out(story, state)


@router.get(
    "/stories/{story_id}", tags=["stories"], dependencies=[Depends(public), Depends(limit_public_reads)]
)
async def get_story(story_id: UUID, session: Session, state: State) -> StoryOut:
    return _story_out(await stories.get_story(session, story_id), state)


@router.post("/findings/{finding_id}/review", tags=["findings"])
async def review_finding(
    finding_id: UUID, body: Review, user: Expert, request: Request, state: State
) -> FindingOut:
    async with state.unit_of_work() as session:
        finding = await verification.apply_review(
            session,
            finding_id,
            reviewer_id=user.id,
            decision=body.decision,
            reason=body.reason,
            damage_type=body.damage_type,
            severity=body.severity,
        )
        await admin.audit(
            session,
            actor_id=user.id,
            action=f"finding.{body.decision}",
            target_type="finding",
            target_id=str(finding_id),
            details={"reason": body.reason},
            request_id=getattr(request.state, "request_id", None),
        )
        still_pending = await verification.pending_for_observation(session, finding.observation_id)
    if not still_pending:
        await state.runner.review_finished(finding.observation_id)
    return finding_out(finding, state.store)


@router.delete("/passport", status_code=204, tags=["passport"])
async def delete_passport(
    passport_id: RequiredPassport, session: Session, state: State, request: Request
) -> None:
    await agents.forget_visitor(session, state.store, passport_id)
    await admin.audit(
        session,
        actor_id=None,
        action="passport.delete",
        target_type="passport",
        target_id=str(passport_id),
        details={"ip": client_ip(request)},
    )


async def _owned_observation(
    session: Session, observation_id: UUID, passport_id: UUID | None
) -> capture.ObservationView:
    observation = await capture.get_observation(session, observation_id)
    if observation.passport_id is not None and observation.passport_id != passport_id:
        raise Forbidden("forbidden")
    return observation


def _event_name(status: ObservationStatus) -> str:
    return {
        ObservationStatus.NEEDS_INPUT: "question",
        ObservationStatus.NEEDS_RETAKE: "retake",
        ObservationStatus.DONE: "done",
        ObservationStatus.FAILED: "error",
    }.get(status, "status")


def _story_out(story: stories.StoryView, state: State) -> StoryOut:
    return StoryOut(
        story_id=str(story.id),
        site_id=str(story.site_id),
        facade_id=str(story.facade_id) if story.facade_id else None,
        lang=story.lang,
        claims=[
            ClaimOut(
                claim_id=c.claim_id,
                text=c.text,
                label=c.label,
                source=SourceOut(**vars(c.source)) if c.source else None,
            )
            for c in story.claims
        ],
        message=None,
        audio_url=state.store.presigned_url(story.audio_key) if story.audio_key else None,
        cached=story.cached,
    )
