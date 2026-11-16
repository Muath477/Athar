from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.capture import api as capture
from sadu.modules.missions.domain.priority import (
    MissionCandidate,
    MissionReason,
    coverage_gap_days,
    rank_candidates,
    select_missions,
)
from sadu.modules.missions.infrastructure.orm import MissionRow
from sadu.modules.sites import api as sites
from sadu.modules.verification import api as verification
from sadu.shared.errors import Conflict, NotFound

MISSION_LIFETIME = timedelta(days=7)

INSTRUCTIONS_AR = {
    MissionReason.CONFIRM_FINDING: "صوّر {facade} من الأمام مثل الصورة المرجعية، لنتأكد من ضرر رُصد سابقًا.",
    MissionReason.COVERAGE_GAP: "لم تُصوَّر {facade} منذ مدة. صوّرها من الأمام مثل الصورة المرجعية.",
}


class MissionStatus(StrEnum):
    OPEN = "open"
    FULFILLED = "fulfilled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class MissionView:
    id: UUID
    site_id: UUID
    facade_id: UUID
    reason: MissionReason
    finding_id: UUID | None
    status: MissionStatus
    instruction_ar: str
    reference_baseline_id: UUID
    expires_at: datetime


async def plan_missions(
    session: AsyncSession, site_id: UUID, now: datetime | None = None
) -> list[MissionView]:
    now = now or datetime.now(UTC)
    await expire_missions(session, now)
    facades = await sites.list_facades(session, site_id)
    facade_ids = [f.id for f in facades]
    last_photos = await capture.last_usable_photo_per_facade(session, site_id)
    candidates = [
        MissionCandidate(
            f"finding:{finding.id}",
            finding.facade_id,
            MissionReason.CONFIRM_FINDING,
            finding.id,
            finding.severity,
        )
        for finding in await verification.needing_confirmation(session, facade_ids)
    ]
    for facade in facades:
        gap = coverage_gap_days(last_photos.get(facade.id), now)
        if gap is not None:
            candidates.append(
                MissionCandidate(
                    f"coverage:{facade.id}", facade.id, MissionReason.COVERAGE_GAP, days_since_last_photo=gap
                )
            )

    open_facades = {m.facade_id for m in await list_missions(session, site_id=site_id)}
    by_id = {f.id: f for f in facades}
    created = []
    for candidate in select_missions(rank_candidates(candidates), open_facades):
        facade = by_id[candidate.facade_id]
        created.append(
            await _open(
                session,
                facade_id=candidate.facade_id,
                reason=candidate.reason,
                finding_id=candidate.finding_id,
                facade_name_ar=facade.name_ar,
                now=now,
            )
        )
    return created


async def create_mission(
    session: AsyncSession, facade_id: UUID, reason: MissionReason, finding_id: UUID | None = None
) -> MissionView:
    facade = await sites.get_facade(session, facade_id)
    if any(m.facade_id == facade_id for m in await list_missions(session, site_id=facade.site_id)):
        raise Conflict("mission_already_open")
    return await _open(
        session,
        facade_id=facade_id,
        reason=reason,
        finding_id=finding_id,
        facade_name_ar=facade.name_ar,
        now=datetime.now(UTC),
    )


async def list_missions(
    session: AsyncSession, *, site_id: UUID | None = None, status: MissionStatus = MissionStatus.OPEN
) -> list[MissionView]:
    statement = select(MissionRow).where(MissionRow.status == status).order_by(MissionRow.created_at)
    if site_id is not None:
        facade_ids = [f.id for f in await sites.list_facades(session, site_id)]
        statement = statement.where(MissionRow.facade_id.in_(facade_ids))
    rows = list(await session.scalars(statement))
    return [await _view(session, row) for row in rows]


async def get_mission(session: AsyncSession, mission_id: UUID) -> MissionView:
    row = await session.get(MissionRow, mission_id)
    if row is None:
        raise NotFound("not_found")
    return await _view(session, row)


async def fulfill(session: AsyncSession, mission_id: UUID, observation_id: UUID) -> None:
    row = await session.get(MissionRow, mission_id)
    if row is None or row.status != MissionStatus.OPEN:
        return
    row.status = MissionStatus.FULFILLED
    row.fulfilled_by = observation_id


async def expire_missions(session: AsyncSession, now: datetime) -> None:
    await session.execute(
        update(MissionRow)
        .where(MissionRow.status == MissionStatus.OPEN, MissionRow.expires_at < now)
        .values(status=MissionStatus.EXPIRED)
    )


async def _open(
    session: AsyncSession,
    *,
    facade_id: UUID,
    reason: MissionReason,
    finding_id: UUID | None,
    facade_name_ar: str,
    now: datetime,
) -> MissionView:
    baseline = await sites.primary_baseline(session, facade_id)
    row = MissionRow(
        facade_id=facade_id,
        reason=reason,
        finding_id=finding_id,
        status=MissionStatus.OPEN,
        instruction_ar=INSTRUCTIONS_AR[reason].format(facade=facade_name_ar),
        reference_baseline_id=baseline.id,
        priority="high" if reason is MissionReason.CONFIRM_FINDING else "normal",
        expires_at=now + MISSION_LIFETIME,
    )
    session.add(row)
    await session.flush()
    return await _view(session, row)


async def _view(session: AsyncSession, row: MissionRow) -> MissionView:
    facade = await sites.get_facade(session, row.facade_id)
    return MissionView(
        id=row.id,
        site_id=facade.site_id,
        facade_id=row.facade_id,
        reason=MissionReason(row.reason),
        finding_id=row.finding_id,
        status=MissionStatus(row.status),
        instruction_ar=row.instruction_ar,
        reference_baseline_id=row.reference_baseline_id,
        expires_at=row.expires_at,
    )
