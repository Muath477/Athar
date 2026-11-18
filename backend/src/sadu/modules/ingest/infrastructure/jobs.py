from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.ingest.domain.jobs import JobStatus
from sadu.modules.ingest.infrastructure.orm import IngestJobRow
from sadu.shared.errors import NotFound

DEFAULT_HISTORY_LIMIT = 50


@dataclass(frozen=True)
class NewJob:
    source: str
    file_name: str
    photo_key: str | None
    created_by: UUID | None
    batch_id: UUID | None = None
    device_id: UUID | None = None
    source_label: str | None = None
    site_id: UUID | None = None
    facade_id: UUID | None = None
    photo_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JobView:
    id: UUID
    batch_id: UUID | None
    device_id: UUID | None
    source: str
    source_label: str | None
    file_name: str
    status: JobStatus
    attempts: int
    error_code: str | None
    error_ar: str | None
    photo_key: str | None
    photo_ready: bool
    site_id: UUID | None
    facade_id: UUID | None
    map_id: UUID | None
    photo_meta: dict[str, Any]
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None

    @property
    def can_retry(self) -> bool:
        return self.status is JobStatus.FAILED and self.photo_key is not None


async def add_job(session: AsyncSession, job: NewJob) -> JobView:
    row = IngestJobRow(
        batch_id=job.batch_id,
        device_id=job.device_id,
        source=job.source,
        source_label=job.source_label,
        file_name=job.file_name,
        photo_key=job.photo_key,
        photo_ready=False,
        site_id=job.site_id,
        facade_id=job.facade_id,
        status=JobStatus.QUEUED,
        attempts=0,
        next_attempt_at=datetime.now(UTC),
        photo_meta=job.photo_meta,
        created_by=job.created_by,
        updated_at=datetime.now(UTC),
    )
    session.add(row)
    await session.flush()
    return _view(row)


async def get_job(session: AsyncSession, job_id: UUID) -> JobView:
    row = await session.get(IngestJobRow, job_id)
    if row is None:
        raise NotFound("not_found")
    return _view(row)


async def list_jobs(
    session: AsyncSession,
    *,
    device_id: UUID | None = None,
    batch_id: UUID | None = None,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> list[JobView]:
    query = select(IngestJobRow).order_by(IngestJobRow.created_at.desc(), IngestJobRow.id).limit(limit)
    if device_id is not None:
        query = query.where(IngestJobRow.device_id == device_id)
    if batch_id is not None:
        query = query.where(IngestJobRow.batch_id == batch_id)
    return [_view(row) for row in await session.scalars(query)]


async def claim_due(session: AsyncSession, limit: int) -> list[UUID]:
    now = datetime.now(UTC)
    rows = await session.scalars(
        select(IngestJobRow)
        .where(IngestJobRow.status == JobStatus.QUEUED, IngestJobRow.next_attempt_at <= now)
        .order_by(IngestJobRow.next_attempt_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    claimed = []
    for row in rows:
        row.status = JobStatus.ANALYSING
        row.attempts += 1
        row.updated_at = now
        claimed.append(row.id)
    return claimed


async def requeue_interrupted(session: AsyncSession) -> None:
    await session.execute(
        update(IngestJobRow)
        .where(IngestJobRow.status == JobStatus.ANALYSING)
        .values(status=JobStatus.QUEUED, next_attempt_at=datetime.now(UTC))
    )


async def queue_again(
    session: AsyncSession, job_id: UUID, *, delay: timedelta, reset: bool = False
) -> JobView:
    row = await job_row(session, job_id)
    now = datetime.now(UTC)
    row.status = JobStatus.QUEUED
    row.next_attempt_at = now + delay
    row.updated_at = now
    row.finished_at = None
    if reset:
        row.attempts = 0
        row.error_code = None
        row.error_ar = None
    return _view(row)


async def store_processed_photo(
    session: AsyncSession, job_id: UUID, photo_key: str, photo_meta: dict[str, Any]
) -> JobView:
    row = await job_row(session, job_id)
    row.photo_key = photo_key
    row.photo_ready = True
    row.photo_meta = {**row.photo_meta, **photo_meta}
    row.updated_at = datetime.now(UTC)
    return _view(row)


async def place(
    session: AsyncSession, job_id: UUID, site_id: UUID | None, facade_id: UUID | None, match: str | None
) -> JobView:
    row = await job_row(session, job_id)
    row.site_id = site_id
    row.facade_id = facade_id
    row.photo_meta = {**row.photo_meta, "facade_match": match}
    row.updated_at = datetime.now(UTC)
    return _view(row)


async def finish(
    session: AsyncSession,
    job_id: UUID,
    status: JobStatus,
    *,
    map_id: UUID | None = None,
    error_code: str | None = None,
    error_ar: str | None = None,
) -> None:
    row = await job_row(session, job_id)
    now = datetime.now(UTC)
    row.status = status
    row.map_id = map_id
    row.error_code = error_code
    row.error_ar = error_ar
    row.updated_at = now
    row.finished_at = now


async def job_row(session: AsyncSession, job_id: UUID) -> IngestJobRow:
    row = await session.get(IngestJobRow, job_id, with_for_update=True)
    if row is None:
        raise NotFound("not_found")
    return row


def _view(row: IngestJobRow) -> JobView:
    return JobView(
        id=row.id,
        batch_id=row.batch_id,
        device_id=row.device_id,
        source=row.source,
        source_label=row.source_label,
        file_name=row.file_name,
        status=JobStatus(row.status),
        attempts=row.attempts,
        error_code=row.error_code,
        error_ar=row.error_ar,
        photo_key=row.photo_key,
        photo_ready=row.photo_ready,
        site_id=row.site_id,
        facade_id=row.facade_id,
        map_id=row.map_id,
        photo_meta=dict(row.photo_meta or {}),
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        finished_at=row.finished_at,
    )
