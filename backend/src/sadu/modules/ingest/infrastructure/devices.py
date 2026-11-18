from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.ingest.domain.devices import CaptureStatus, DeviceKind, capture_due
from sadu.modules.ingest.infrastructure.orm import DeviceRow
from sadu.shared.errors import NotFound


@dataclass(frozen=True)
class DeviceSpec:
    kind: DeviceKind
    name_ar: str
    site_id: UUID | None = None
    facade_id: UUID | None = None
    snapshot_url: str | None = None
    rtsp_url: str | None = None
    username: str | None = None
    secret_env: str | None = None
    interval_h: int | None = None
    active: bool = True


@dataclass(frozen=True)
class DeviceView:
    id: UUID
    kind: DeviceKind
    name_ar: str
    site_id: UUID | None
    facade_id: UUID | None
    snapshot_url: str | None
    rtsp_url: str | None
    username: str | None
    secret_env: str | None
    interval_h: int | None
    active: bool
    last_capture_at: datetime | None
    last_status: CaptureStatus | None
    last_error_ar: str | None
    last_photo_key: str | None
    created_at: datetime

    @property
    def captures(self) -> bool:
        return bool(self.snapshot_url or self.rtsp_url)


async def list_devices(session: AsyncSession, site_id: UUID | None = None) -> list[DeviceView]:
    query = select(DeviceRow).order_by(DeviceRow.created_at)
    if site_id is not None:
        query = query.where(DeviceRow.site_id == site_id)
    return [_view(row) for row in await session.scalars(query)]


async def get_device(session: AsyncSession, device_id: UUID) -> DeviceView:
    return _view(await _row(session, device_id))


async def create_device(session: AsyncSession, spec: DeviceSpec, created_by: UUID | None) -> DeviceView:
    row = DeviceRow(created_by=created_by, active=spec.active)
    _apply(row, spec)
    session.add(row)
    await session.flush()
    return _view(row)


async def update_device(session: AsyncSession, device_id: UUID, spec: DeviceSpec) -> DeviceView:
    row = await _row(session, device_id)
    _apply(row, spec)
    await session.flush()
    return _view(row)


async def delete_device(session: AsyncSession, device_id: UUID) -> None:
    await session.delete(await _row(session, device_id))


async def record_capture(
    session: AsyncSession, device_id: UUID, status: CaptureStatus, error_ar: str | None
) -> None:
    row = await _row(session, device_id)
    row.last_capture_at = datetime.now(UTC)
    row.last_status = status
    row.last_error_ar = error_ar


async def record_photo(session: AsyncSession, device_id: UUID, photo_key: str) -> None:
    row = await session.get(DeviceRow, device_id)
    if row is not None:
        row.last_photo_key = photo_key


async def due_devices(session: AsyncSession, default_interval: timedelta) -> list[UUID]:
    now = datetime.now(UTC)
    rows = await session.scalars(select(DeviceRow).where(DeviceRow.active.is_(True)))
    return [
        row.id
        for row in rows
        if (row.snapshot_url or row.rtsp_url)
        and capture_due(row.last_capture_at, _interval(row, default_interval), now)
    ]


async def find_device_by_url(session: AsyncSession, site_id: UUID, snapshot_url: str) -> DeviceView | None:
    row = await session.scalar(
        select(DeviceRow).where(DeviceRow.site_id == site_id, DeviceRow.snapshot_url == snapshot_url)
    )
    return _view(row) if row is not None else None


def _interval(row: DeviceRow, default_interval: timedelta) -> timedelta:
    return timedelta(hours=row.interval_h) if row.interval_h else default_interval


def _apply(row: DeviceRow, spec: DeviceSpec) -> None:
    row.kind = spec.kind
    row.name_ar = spec.name_ar
    row.site_id = spec.site_id
    row.facade_id = spec.facade_id
    row.snapshot_url = spec.snapshot_url
    row.rtsp_url = spec.rtsp_url
    row.username = spec.username
    row.secret_env = spec.secret_env
    row.interval_h = spec.interval_h
    row.active = spec.active


async def _row(session: AsyncSession, device_id: UUID) -> DeviceRow:
    row = await session.get(DeviceRow, device_id)
    if row is None:
        raise NotFound("not_found")
    return row


def _view(row: DeviceRow) -> DeviceView:
    return DeviceView(
        id=row.id,
        kind=DeviceKind(row.kind),
        name_ar=row.name_ar,
        site_id=row.site_id,
        facade_id=row.facade_id,
        snapshot_url=row.snapshot_url,
        rtsp_url=row.rtsp_url,
        username=row.username,
        secret_env=row.secret_env,
        interval_h=row.interval_h,
        active=row.active,
        last_capture_at=row.last_capture_at,
        last_status=CaptureStatus(row.last_status) if row.last_status else None,
        last_error_ar=row.last_error_ar,
        last_photo_key=row.last_photo_key,
        created_at=row.created_at,
    )
