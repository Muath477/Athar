import asyncio
import shutil
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.admin import api as admin
from sadu.modules.capture import api as capture
from sadu.modules.ingest.application.ports import CameraClient, CameraTarget, CameraUnreachable
from sadu.modules.ingest.domain.devices import CREDENTIAL_ENV_PATTERN, CaptureStatus, DeviceKind
from sadu.modules.ingest.domain.geo import (
    SITE_MATCH_RADIUS_M,
    FacadeFootprint,
    GeoPoint,
    PhotoMetadata,
    distance_m,
    nearest_facade,
)
from sadu.modules.ingest.domain.jobs import FacadeMatch, JobStatus, retry_delay
from sadu.modules.ingest.domain.url_safety import (
    RTSP_SCHEMES,
    SNAPSHOT_SCHEMES,
    AllowList,
    UnsafeCameraUrl,
    parse_camera_url,
)
from sadu.modules.ingest.infrastructure import devices, jobs
from sadu.modules.ingest.infrastructure.cameras import (
    CAMERA_TIMEOUT_S,
    HttpSnapshots,
    NetworkCameras,
    RtspSnapshots,
    SafeAddresses,
    camera_password,
)
from sadu.modules.ingest.infrastructure.devices import (
    DeviceSpec,
    DeviceView,
    create_device,
    delete_device,
    get_device,
    list_devices,
    update_device,
)
from sadu.modules.ingest.infrastructure.jobs import JobView, NewJob, get_job, list_jobs
from sadu.modules.ingest.infrastructure.photos import (
    as_jpeg_or_png,
    read_photo_metadata,
    require_supported_format,
)
from sadu.modules.mapping import api as mapping
from sadu.modules.sites import api as sites
from sadu.shared.config import Settings
from sadu.shared.errors import Conflict, SaduError
from sadu.shared.i18n import translate
from sadu.shared.resilience import call_with_policy
from sadu.shared.storage import ObjectStore, new_object_key
from sadu.shared.web import UnitOfWork

__all__ = [
    "CREDENTIAL_ENV_PATTERN",
    "CameraClient",
    "CameraTarget",
    "CameraUnreachable",
    "CaptureStatus",
    "DeviceKind",
    "DeviceSpec",
    "DeviceView",
    "JobStatus",
    "JobView",
    "create_device",
    "delete_device",
    "get_device",
    "get_job",
    "list_devices",
    "list_jobs",
    "update_device",
]

log = structlog.get_logger()

MAX_BATCH_FILES = 30
CAMERA_RETRIES = 1
CAMERA_SNAPSHOT_NAME = "snapshot.jpg"
DEMO_SITE_SLUG = "demo-house"
DEMO_FACADE_CODE = "north"
DEMO_CAMERA_URL = "http://localhost:8000/api/v1/ingest/demo-snapshots/north-crack.jpg"
DEMO_CAMERA_NAME = "كاميرا الواجهة الشمالية (تجريبية)"

SOURCE_BY_KIND = {
    DeviceKind.FIXED_CAMERA: mapping.MapSource.CAMERA,
    DeviceKind.DRONE: mapping.MapSource.DRONE,
    DeviceKind.PHONE: mapping.MapSource.INSPECTOR,
    DeviceKind.UPLOAD: mapping.MapSource.UPLOAD,
}


@dataclass(frozen=True)
class UploadedPhoto:
    file_name: str
    data: bytes


@dataclass(frozen=True)
class UploadTarget:
    site_id: UUID | None = None
    facade_id: UUID | None = None
    device_id: UUID | None = None


@dataclass(frozen=True)
class _Placement:
    site_id: UUID | None
    facade_id: UUID | None
    match: FacadeMatch | None
    source: mapping.MapSource
    source_label: str | None
    device_id: UUID | None


def build_camera_client(settings: Settings) -> NetworkCameras:
    allowed = AllowList.parse(settings.sadu_camera_allowed_hosts)
    if settings.sadu_demo_mode:
        allowed = allowed.with_host("localhost")
    addresses = SafeAddresses(allowed)
    return NetworkCameras(
        HttpSnapshots(addresses, capture.MAX_UPLOAD_BYTES),
        RtspSnapshots(addresses, capture.MAX_UPLOAD_BYTES, shutil.which("ffmpeg")),
    )


async def validate_device(session: AsyncSession, spec: DeviceSpec) -> None:
    if spec.kind is DeviceKind.FIXED_CAMERA and spec.site_id is None:
        raise SaduError("device_site_required", status=422)
    if spec.site_id is not None:
        await sites.get_site(session, spec.site_id)
    if spec.facade_id is not None:
        facade = await sites.get_facade(session, spec.facade_id)
        if facade.site_id != spec.site_id:
            raise SaduError("facade_not_in_site", status=422)
    for url, schemes in ((spec.snapshot_url, SNAPSHOT_SCHEMES), (spec.rtsp_url, RTSP_SCHEMES)):
        if not url:
            continue
        try:
            parse_camera_url(url, schemes)
        except UnsafeCameraUrl as error:
            raise SaduError("invalid_camera_url", status=422, reason=error.reason) from error


def has_secret(device: DeviceView) -> bool:
    return camera_password(device.secret_env) is not None


async def seed_demo_camera(session: AsyncSession) -> DeviceView:
    site = await sites.get_site_by_slug(session, DEMO_SITE_SLUG)
    existing = await devices.find_device_by_url(session, site.id, DEMO_CAMERA_URL)
    if existing is not None:
        return existing
    facade = next(f for f in await sites.list_facades(session, site.id) if f.code == DEMO_FACADE_CODE)
    spec = DeviceSpec(
        kind=DeviceKind.FIXED_CAMERA,
        name_ar=DEMO_CAMERA_NAME,
        site_id=site.id,
        facade_id=facade.id,
        snapshot_url=DEMO_CAMERA_URL,
        interval_h=24,
    )
    return await devices.create_device(session, spec, created_by=None)


class Ingestion:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        store: ObjectStore,
        detector: mapping.DamageDetector,
        cameras: CameraClient,
        *,
        map_rows: int,
        concurrency: int = 2,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._store = store
        self._detector = detector
        self._cameras = cameras
        self._map_rows = map_rows
        self._concurrency = concurrency
        self._drainer: asyncio.Task[None] | None = None
        self._more_queued = False

    async def recover(self) -> None:
        async with self._unit_of_work() as session:
            await jobs.requeue_interrupted(session)

    def kick(self) -> None:
        if self._drainer is not None and not self._drainer.done():
            self._more_queued = True
            return
        self._drainer = asyncio.create_task(self._drain())

    async def join(self) -> None:
        if self._drainer is not None:
            await self._drainer

    async def capture(self, device_id: UUID, actor_id: UUID | None) -> JobView:
        async with self._unit_of_work() as session:
            device = await devices.get_device(session, device_id)
        if not device.captures:
            raise Conflict("device_has_no_source")
        target = CameraTarget(
            device.snapshot_url, device.rtsp_url, device.username, camera_password(device.secret_env)
        )
        try:
            raw = await call_with_policy(
                "camera_snapshot",
                lambda: self._cameras.snapshot(target),
                timeout_s=CAMERA_TIMEOUT_S * 1.5,
                retries=CAMERA_RETRIES,
            )
        except (CameraUnreachable, TimeoutError) as error:
            return await self._record_failed_capture(device, actor_id, _camera_error_ar(error))
        key = new_object_key("ingest/raw", "bin")
        await self._store.put(key, raw, "application/octet-stream")
        async with self._unit_of_work() as session:
            job = await jobs.add_job(session, _camera_job(device, key, actor_id))
            await devices.record_capture(session, device.id, CaptureStatus.OK, None)
        self.kick()
        return job

    async def capture_due(self, default_interval: timedelta) -> int:
        async with self._unit_of_work() as session:
            due = await devices.due_devices(session, default_interval)
        slots = asyncio.Semaphore(self._concurrency)

        async def capture_one(device_id: UUID) -> None:
            async with slots:
                try:
                    await self.capture(device_id, None)
                except Exception:
                    log.exception("camera_capture_failed", device_id=str(device_id))

        await asyncio.gather(*(capture_one(device_id) for device_id in due))
        return len(due)

    async def queue_uploads(self, photos: list[UploadedPhoto], target: UploadTarget, actor_id: UUID) -> UUID:
        if not photos or len(photos) > MAX_BATCH_FILES:
            raise SaduError("batch_size", status=422, max_files=MAX_BATCH_FILES)
        for photo in photos:
            if len(photo.data) > capture.MAX_UPLOAD_BYTES:
                raise SaduError(
                    "upload_too_large", status=413, max_mb=capture.MAX_UPLOAD_BYTES // (1024 * 1024)
                )
            require_supported_format(photo.data, photo.file_name)
        batch_id = uuid4()
        async with self._unit_of_work() as session:
            placement = await _upload_placement(session, target)
            for photo in photos:
                key = new_object_key("ingest/raw", "bin")
                await self._store.put(key, photo.data, "application/octet-stream")
                await jobs.add_job(session, _upload_job(placement, photo.file_name, key, batch_id, actor_id))
        self.kick()
        return batch_id

    async def retry(self, job_id: UUID) -> JobView:
        async with self._unit_of_work() as session:
            job = await jobs.get_job(session, job_id)
            if not job.can_retry:
                raise Conflict("job_not_retryable")
            queued = await jobs.queue_again(session, job_id, delay=timedelta(0), reset=True)
        self.kick()
        return queued

    async def assign_facade(self, job_id: UUID, facade_id: UUID) -> JobView:
        async with self._unit_of_work() as session:
            job = await jobs.get_job(session, job_id)
            if job.status not in {JobStatus.NEEDS_FACADE, JobStatus.FAILED} or job.photo_key is None:
                raise Conflict("job_not_retryable")
            facade = await sites.get_facade(session, facade_id)
            await jobs.place(session, job_id, facade.site_id, facade.id, FacadeMatch.CHOSEN)
            queued = await jobs.queue_again(session, job_id, delay=timedelta(0), reset=True)
        self.kick()
        return queued

    async def _drain(self) -> None:
        while True:
            self._more_queued = False
            try:
                async with self._unit_of_work() as session:
                    claimed = await jobs.claim_due(session, self._concurrency)
            except Exception:
                log.exception("ingest_claim_failed")
                return
            if not claimed:
                if self._more_queued:
                    continue
                return
            await asyncio.gather(*(self._process(job_id) for job_id in claimed), return_exceptions=True)

    async def _process(self, job_id: UUID) -> None:
        try:
            job, photo_key = await self._prepare_photo(job_id)
            facade_id = job.facade_id or await self._match_facade(job)
            if facade_id is None:
                async with self._unit_of_work() as session:
                    await jobs.finish(session, job_id, JobStatus.NEEDS_FACADE)
                return
            await self._analyse(job, photo_key, facade_id)
        except SaduError as error:
            message_ar = translate(f"problem.{error.code}.detail", "ar", **error.params)
            async with self._unit_of_work() as session:
                await jobs.finish(
                    session, job_id, JobStatus.FAILED, error_code=error.code, error_ar=message_ar
                )
        except Exception:
            log.exception("ingest_job_failed", job_id=str(job_id))
            await self._retry_later(job_id)

    async def _prepare_photo(self, job_id: UUID) -> tuple[JobView, str]:
        async with self._unit_of_work() as session:
            job = await jobs.get_job(session, job_id)
        if job.photo_key is None:
            raise SaduError("photo_required", status=422)
        if job.photo_ready:
            return job, job.photo_key
        raw_key = job.photo_key
        raw = await self._store.get(raw_key)
        metadata = await asyncio.to_thread(read_photo_metadata, raw)
        processed = await asyncio.to_thread(_privacy_safe_jpeg, raw)
        key = new_object_key("ingest/photos", "jpg")
        await self._store.put(key, processed, "image/jpeg")
        async with self._unit_of_work() as session:
            job = await jobs.store_processed_photo(session, job_id, key, _metadata_json(metadata))
            if job.device_id is not None:
                await devices.record_photo(session, job.device_id, key)
        await self._delete_raw(raw_key)
        return job, key

    async def _match_facade(self, job: JobView) -> UUID | None:
        location = _location(job.photo_meta)
        if location is None:
            return None
        async with self._unit_of_work() as session:
            nearby = await sites.find_sites_near(session, location.lat, location.lon, SITE_MATCH_RADIUS_M)
            if job.site_id is not None:
                nearby = [site for site in nearby if site.id == job.site_id]
            if not nearby:
                return None
            site = min(nearby, key=lambda s: distance_m(GeoPoint(s.location.lat, s.location.lon), location))
            footprints = [
                FacadeFootprint.from_site_corners(f.id, f.corners, f.outward_azimuth_deg)
                for f in await sites.list_facades(session, site.id)
            ]
            facade_id = nearest_facade(GeoPoint(site.location.lat, site.location.lon), location, footprints)
            await jobs.place(session, job.id, site.id, facade_id, FacadeMatch.GPS if facade_id else None)
        return facade_id

    async def _analyse(self, job: JobView, photo_key: str, facade_id: UUID) -> None:
        async with self._unit_of_work() as session:
            facade = await sites.get_facade(session, facade_id)
        plane = facade.plane
        wall = mapping.WallSpec(
            facade.name_ar, mapping.WallSize(plane.width_m, plane.height_m), facade.site_id, facade.id
        )
        photo = await self._store.get(photo_key)
        prepared = await asyncio.to_thread(
            mapping.prepare_wall, photo, mapping.Quad.full_frame(), wall.size, self._map_rows
        )
        run = await mapping.detect_damage(self._detector, prepared)
        provenance = mapping.Provenance(mapping.MapSource(job.source), job.source_label)
        async with self._unit_of_work() as session:
            view = await mapping.save_map(
                session,
                self._store,
                wall=wall,
                prepared=prepared,
                run=run,
                created_by=job.created_by,
                provenance=provenance,
            )
            await admin.audit(
                session,
                actor_id=job.created_by,
                action="map.create",
                target_type="damage_map",
                target_id=str(view.id),
                details={"detector": run.detector, "source": job.source, "ingest_job": str(job.id)},
            )
            await jobs.finish(session, job.id, JobStatus.DONE, map_id=view.id)

    async def _retry_later(self, job_id: UUID) -> None:
        async with self._unit_of_work() as session:
            job = await jobs.get_job(session, job_id)
            delay = retry_delay(job.attempts)
            if delay is None:
                message_ar = translate("problem.ingest_failed.detail", "ar")
                await jobs.finish(
                    session, job_id, JobStatus.FAILED, error_code="ingest_failed", error_ar=message_ar
                )
            else:
                await jobs.queue_again(session, job_id, delay=delay)

    async def _record_failed_capture(
        self, device: DeviceView, actor_id: UUID | None, message_ar: str
    ) -> JobView:
        async with self._unit_of_work() as session:
            job = await jobs.add_job(session, _camera_job(device, None, actor_id))
            await jobs.finish(
                session, job.id, JobStatus.FAILED, error_code="camera_unreachable", error_ar=message_ar
            )
            await devices.record_capture(session, device.id, CaptureStatus.FAILED, message_ar)
            return await jobs.get_job(session, job.id)

    async def _delete_raw(self, key: str) -> None:
        try:
            await self._store.delete(key)
        except Exception:
            log.warning("raw_photo_delete_failed", key=key)


async def _upload_placement(session: AsyncSession, target: UploadTarget) -> _Placement:
    device = await devices.get_device(session, target.device_id) if target.device_id else None
    site_id = target.site_id
    facade_id = target.facade_id or (device.facade_id if device else None)
    if facade_id is not None:
        facade = await sites.get_facade(session, facade_id)
        if site_id is not None and facade.site_id != site_id:
            raise SaduError("facade_not_in_site", status=422)
        site_id = facade.site_id
    elif site_id is not None:
        await sites.get_site(session, site_id)
    match = None
    if target.facade_id:
        match = FacadeMatch.CHOSEN
    elif facade_id:
        match = FacadeMatch.DEVICE
    return _Placement(
        site_id=site_id,
        facade_id=facade_id,
        match=match,
        source=SOURCE_BY_KIND[device.kind] if device else mapping.MapSource.UPLOAD,
        source_label=device.name_ar if device else None,
        device_id=device.id if device else None,
    )


def _upload_job(
    placement: _Placement, file_name: str, photo_key: str, batch_id: UUID, actor_id: UUID
) -> NewJob:
    return NewJob(
        source=placement.source,
        file_name=file_name[:200],
        photo_key=photo_key,
        created_by=actor_id,
        batch_id=batch_id,
        device_id=placement.device_id,
        source_label=placement.source_label,
        site_id=placement.site_id,
        facade_id=placement.facade_id,
        photo_meta={"facade_match": placement.match},
    )


def _camera_job(device: DeviceView, photo_key: str | None, actor_id: UUID | None) -> NewJob:
    return NewJob(
        source=SOURCE_BY_KIND[device.kind],
        file_name=CAMERA_SNAPSHOT_NAME,
        photo_key=photo_key,
        created_by=actor_id,
        device_id=device.id,
        source_label=device.name_ar,
        site_id=device.site_id,
        facade_id=device.facade_id,
        photo_meta={"facade_match": FacadeMatch.DEVICE if device.facade_id else None},
    )


def _camera_error_ar(error: CameraUnreachable | TimeoutError) -> str:
    if isinstance(error, TimeoutError):
        return translate("camera.timeout", "ar")
    return translate(f"camera.{error.reason}", "ar", **error.details)


def _privacy_safe_jpeg(raw: bytes) -> bytes:
    return capture.process_upload(as_jpeg_or_png(raw)).jpeg


def _metadata_json(metadata: PhotoMetadata) -> dict[str, Any]:
    location = metadata.location
    return {
        "lat": location.lat if location else None,
        "lon": location.lon if location else None,
        "taken_at": metadata.taken_at.isoformat() if metadata.taken_at else None,
    }


def _location(photo_meta: dict[str, Any]) -> GeoPoint | None:
    lat, lon = photo_meta.get("lat"), photo_meta.get("lon")
    if lat is None or lon is None:
        return None
    return GeoPoint(float(lat), float(lon))
