from collections import Counter
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from sadu.modules.ingest import api as ingest
from sadu.shared.storage import ObjectStore

MAX_INTERVAL_H = 24 * 30


class DeviceIn(BaseModel):
    kind: ingest.DeviceKind
    name_ar: str = Field(min_length=1, max_length=200)
    site_id: UUID | None = None
    facade_id: UUID | None = None
    snapshot_url: str | None = Field(default=None, max_length=500)
    rtsp_url: str | None = Field(default=None, max_length=500)
    username: str | None = Field(default=None, max_length=100)
    secret_env: str | None = Field(default=None, pattern=ingest.CREDENTIAL_ENV_PATTERN)
    interval_h: int | None = Field(default=None, ge=1, le=MAX_INTERVAL_H)
    active: bool = True

    def spec(self) -> ingest.DeviceSpec:
        return ingest.DeviceSpec(
            kind=self.kind,
            name_ar=self.name_ar.strip(),
            site_id=self.site_id,
            facade_id=self.facade_id,
            snapshot_url=_text_or_none(self.snapshot_url),
            rtsp_url=_text_or_none(self.rtsp_url),
            username=_text_or_none(self.username),
            secret_env=_text_or_none(self.secret_env),
            interval_h=self.interval_h,
            active=self.active,
        )


class FacadeChoiceIn(BaseModel):
    facade_id: UUID


class DeviceOut(BaseModel):
    id: str
    kind: str
    name_ar: str
    site_id: str | None
    facade_id: str | None
    snapshot_url: str | None
    rtsp_url: str | None
    username: str | None
    secret_env: str | None
    secret_configured: bool
    interval_h: int | None
    active: bool
    last_capture_at: datetime | None
    last_status: str | None
    last_error_ar: str | None
    thumbnail_url: str | None
    created_at: datetime


class JobOut(BaseModel):
    id: str
    batch_id: str | None
    device_id: str | None
    source: str
    source_label: str | None
    file_name: str
    status: str
    attempts: int
    error_ar: str | None
    can_retry: bool
    photo_url: str | None
    site_id: str | None
    facade_id: str | None
    map_id: str | None
    lat: float | None
    lon: float | None
    taken_at: str | None
    facade_match: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None


class BatchOut(BaseModel):
    id: str
    total: int
    counts: dict[str, int]
    jobs: list[JobOut]


def device_out(view: ingest.DeviceView, store: ObjectStore) -> DeviceOut:
    return DeviceOut(
        id=str(view.id),
        kind=view.kind,
        name_ar=view.name_ar,
        site_id=_str_or_none(view.site_id),
        facade_id=_str_or_none(view.facade_id),
        snapshot_url=view.snapshot_url,
        rtsp_url=view.rtsp_url,
        username=view.username,
        secret_env=view.secret_env,
        secret_configured=ingest.has_secret(view),
        interval_h=view.interval_h,
        active=view.active,
        last_capture_at=view.last_capture_at,
        last_status=view.last_status,
        last_error_ar=view.last_error_ar,
        thumbnail_url=store.presigned_url(view.last_photo_key) if view.last_photo_key else None,
        created_at=view.created_at,
    )


def job_out(view: ingest.JobView, store: ObjectStore) -> JobOut:
    meta = view.photo_meta
    return JobOut(
        id=str(view.id),
        batch_id=_str_or_none(view.batch_id),
        device_id=_str_or_none(view.device_id),
        source=view.source,
        source_label=view.source_label,
        file_name=view.file_name,
        status=view.status,
        attempts=view.attempts,
        error_ar=view.error_ar,
        can_retry=view.can_retry,
        photo_url=store.presigned_url(view.photo_key) if view.photo_ready and view.photo_key else None,
        site_id=_str_or_none(view.site_id),
        facade_id=_str_or_none(view.facade_id),
        map_id=_str_or_none(view.map_id),
        lat=meta.get("lat"),
        lon=meta.get("lon"),
        taken_at=meta.get("taken_at"),
        facade_match=meta.get("facade_match"),
        created_at=view.created_at,
        updated_at=view.updated_at,
        finished_at=view.finished_at,
    )


def batch_out(batch_id: UUID, views: list[ingest.JobView], store: ObjectStore) -> BatchOut:
    ordered = sorted(views, key=lambda v: (v.created_at, v.file_name))
    return BatchOut(
        id=str(batch_id),
        total=len(ordered),
        counts=dict(Counter(view.status.value for view in ordered)),
        jobs=[job_out(view, store) for view in ordered],
    )


def _text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _str_or_none(value: UUID | None) -> str | None:
    return str(value) if value is not None else None
