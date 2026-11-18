import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.capture.infrastructure.image_processing import (
    MAX_UPLOAD_BYTES,
    ProcessedPhoto,
    process_upload,
)
from sadu.modules.capture.infrastructure.orm import ObservationRow
from sadu.shared.errors import Conflict, NotFound
from sadu.shared.storage import ObjectStore, new_object_key

PHOTO_RETENTION = timedelta(days=30)

__all__ = ["MAX_UPLOAD_BYTES", "ProcessedPhoto", "process_upload"]


class ObservationStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    NEEDS_INPUT = "needs_input"
    NEEDS_RETAKE = "needs_retake"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class CaptureMeta:
    captured_at: datetime
    site_id: UUID | None = None
    mission_id: UUID | None = None
    lat: float | None = None
    lon: float | None = None
    gps_accuracy_m: float | None = None
    heading_deg: float | None = None
    heading_accuracy_deg: float | None = None
    passport_id: UUID | None = None


@dataclass(frozen=True)
class ObservationView:
    id: UUID
    site_id: UUID | None
    facade_id: UUID | None
    passport_id: UUID | None
    mission_id: UUID | None
    object_key: str
    has_location: bool
    lat: float | None
    lon: float | None
    heading_deg: float | None
    heading_accuracy_deg: float | None
    status: ObservationStatus
    status_payload: dict[str, Any]
    content_sha256: str


async def create_observation(
    session: AsyncSession, store: ObjectStore, *, raw_photo: bytes, meta: CaptureMeta, idempotency_key: str
) -> tuple[ObservationView, bool]:
    request_hash = _request_hash(raw_photo, meta)
    existing = await session.scalar(
        select(ObservationRow).where(ObservationRow.idempotency_key == idempotency_key)
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            raise Conflict("idempotency_key_reused")
        return await _view(session, existing), False

    processed = await asyncio.to_thread(process_upload, raw_photo)
    key = new_object_key("observations", "jpg")
    await store.put(key, processed.jpeg, "image/jpeg")
    has_location = meta.lat is not None and meta.lon is not None
    row = ObservationRow(
        site_id=meta.site_id,
        mission_id=meta.mission_id,
        passport_id=meta.passport_id,
        object_key=key,
        width=processed.width,
        height=processed.height,
        location=f"SRID=4326;POINT({meta.lon} {meta.lat})" if has_location else None,
        gps_accuracy_m=meta.gps_accuracy_m,
        heading_deg=meta.heading_deg,
        heading_accuracy_deg=meta.heading_accuracy_deg,
        captured_at=meta.captured_at,
        status=ObservationStatus.RECEIVED,
        status_payload={},
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        content_sha256=hashlib.sha256(processed.jpeg).hexdigest(),
        faces_blurred=processed.faces_blurred,
        delete_after=datetime.now(UTC) + PHOTO_RETENTION,
    )
    session.add(row)
    await session.flush()
    return await _view(session, row), True


async def get_observation(session: AsyncSession, observation_id: UUID) -> ObservationView:
    row = await session.get(ObservationRow, observation_id)
    if row is None:
        raise NotFound("not_found")
    return await _view(session, row)


async def set_status(
    session: AsyncSession,
    observation_id: UUID,
    status: ObservationStatus,
    payload: dict[str, Any] | None = None,
) -> None:
    row = await _row(session, observation_id)
    row.status = status
    row.status_payload = payload or {}


async def attach_location_result(
    session: AsyncSession, observation_id: UUID, *, site_id: UUID | None, facade_id: UUID | None
) -> None:
    row = await _row(session, observation_id)
    row.site_id = site_id
    row.facade_id = facade_id
    row.location = None
    row.heading_deg = None


async def keep_as_evidence(session: AsyncSession, observation_id: UUID, *, years: int = 2) -> None:
    row = await _row(session, observation_id)
    row.delete_after = datetime.now(UTC) + timedelta(days=365 * years)


async def last_usable_photo_per_facade(session: AsyncSession, site_id: UUID) -> dict[UUID, datetime]:
    rows = await session.execute(
        select(ObservationRow.facade_id, func.max(ObservationRow.captured_at))
        .where(ObservationRow.site_id == site_id, ObservationRow.status == ObservationStatus.DONE)
        .where(ObservationRow.facade_id.is_not(None))
        .group_by(ObservationRow.facade_id)
    )
    return {facade_id: captured_at for facade_id, captured_at in rows.all() if facade_id is not None}


async def unfinished_observation_ids(session: AsyncSession, older_than: timedelta) -> list[UUID]:
    cutoff = datetime.now(UTC) - older_than
    rows = await session.scalars(
        select(ObservationRow.id).where(
            ObservationRow.status.in_([ObservationStatus.RECEIVED, ObservationStatus.PROCESSING]),
            ObservationRow.received_at < cutoff,
        )
    )
    return list(rows)


async def release_passport_photos(session: AsyncSession, passport_id: UUID) -> dict[UUID, str]:
    cutoff = datetime.now(UTC) + PHOTO_RETENTION
    rows = await session.scalars(select(ObservationRow).where(ObservationRow.passport_id == passport_id))
    to_delete = {}
    for row in rows:
        row.passport_id = None
        if row.delete_after <= cutoff:
            to_delete[row.id] = row.object_key
    return to_delete


async def expired_photos(session: AsyncSession, now: datetime, limit: int) -> dict[UUID, str]:
    rows = await session.execute(
        select(ObservationRow.id, ObservationRow.object_key)
        .where(ObservationRow.delete_after <= now)
        .order_by(ObservationRow.delete_after)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return {observation_id: key for observation_id, key in rows.all()}


async def delete_observations(session: AsyncSession, observation_ids: list[UUID]) -> None:
    await session.execute(delete(ObservationRow).where(ObservationRow.id.in_(observation_ids)))


async def _row(session: AsyncSession, observation_id: UUID) -> ObservationRow:
    row = await session.get(ObservationRow, observation_id)
    if row is None:
        raise NotFound("not_found")
    return row


async def _view(session: AsyncSession, row: ObservationRow) -> ObservationView:
    lat = lon = None
    if row.location is not None:
        lat, lon = (
            await session.execute(
                select(
                    func.ST_Y(func.geometry(ObservationRow.location)),
                    func.ST_X(func.geometry(ObservationRow.location)),
                ).where(ObservationRow.id == row.id)
            )
        ).one()
    return ObservationView(
        id=row.id,
        site_id=row.site_id,
        facade_id=row.facade_id,
        passport_id=row.passport_id,
        mission_id=row.mission_id,
        object_key=row.object_key,
        has_location=row.location is not None,
        lat=lat,
        lon=lon,
        heading_deg=row.heading_deg,
        heading_accuracy_deg=row.heading_accuracy_deg,
        status=ObservationStatus(row.status),
        status_payload=row.status_payload,
        content_sha256=row.content_sha256,
    )


def _request_hash(raw_photo: bytes, meta: CaptureMeta) -> str:
    digest = hashlib.sha256(raw_photo)
    digest.update(repr(sorted(vars(meta).items())).encode())
    return digest.hexdigest()
