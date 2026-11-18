import re
from pathlib import Path, PurePath
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.admin import api as admin
from sadu.modules.admin.interface.auth import DeviceManager, Inspector, Staff
from sadu.modules.capture import api as capture
from sadu.modules.ingest import api as ingest
from sadu.modules.ingest.interface.schemas import (
    BatchOut,
    DeviceIn,
    DeviceOut,
    FacadeChoiceIn,
    JobOut,
    batch_out,
    device_out,
    job_out,
)
from sadu.shared.errors import NotFound, SaduError
from sadu.shared.web import Session, State, public

router = APIRouter(tags=["ingest"])

UPLOAD_BATCHES_PER_USER_PER_HOUR = 20
CAPTURES_PER_USER_PER_HOUR = 60
MAX_HISTORY = 200
DEMO_SNAPSHOT_NAME = re.compile(r"^[a-z0-9-]+\.jpg$")
DEFAULT_FILE_NAME = "photo.jpg"


def ingestion(request: Request) -> ingest.Ingestion:
    service: ingest.Ingestion = request.app.state.ingestion
    return service


Ingestion = Annotated[ingest.Ingestion, Depends(ingestion)]


@router.get("/ingest/devices")
async def list_devices(
    _: Staff, session: Session, state: State, site_id: UUID | None = None
) -> list[DeviceOut]:
    return [device_out(d, state.store) for d in await ingest.list_devices(session, site_id)]


@router.post("/ingest/devices", status_code=201)
async def create_device(
    body: DeviceIn, user: DeviceManager, session: Session, state: State, request: Request
) -> DeviceOut:
    spec = body.spec()
    await ingest.validate_device(session, spec)
    view = await ingest.create_device(session, spec, user.id)
    await _audit(session, request, user.id, "device.create", view.id, {"kind": view.kind})
    return device_out(view, state.store)


@router.get("/ingest/devices/{device_id}")
async def get_device(device_id: UUID, _: Staff, session: Session, state: State) -> DeviceOut:
    return device_out(await ingest.get_device(session, device_id), state.store)


@router.post("/ingest/devices/{device_id}")
async def update_device(
    device_id: UUID, body: DeviceIn, user: DeviceManager, session: Session, state: State, request: Request
) -> DeviceOut:
    spec = body.spec()
    await ingest.validate_device(session, spec)
    view = await ingest.update_device(session, device_id, spec)
    await _audit(session, request, user.id, "device.update", device_id)
    return device_out(view, state.store)


@router.delete("/ingest/devices/{device_id}", status_code=204)
async def delete_device(device_id: UUID, user: DeviceManager, session: Session, request: Request) -> None:
    await ingest.delete_device(session, device_id)
    await _audit(session, request, user.id, "device.delete", device_id)


@router.post("/ingest/devices/{device_id}/capture", status_code=202)
async def capture_now(
    device_id: UUID, user: DeviceManager, state: State, service: Ingestion, request: Request
) -> JobOut:
    state.rate_limiter.check(f"capture:{user.id}", CAPTURES_PER_USER_PER_HOUR, 3600)
    job = await service.capture(device_id, user.id)
    async with state.unit_of_work() as session:
        await _audit(session, request, user.id, "device.capture", device_id, {"job": str(job.id)})
    return job_out(job, state.store)


@router.get("/ingest/jobs")
async def list_jobs(
    _: Staff,
    session: Session,
    state: State,
    device_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_HISTORY)] = 50,
) -> list[JobOut]:
    return [
        job_out(j, state.store) for j in await ingest.list_jobs(session, device_id=device_id, limit=limit)
    ]


@router.get("/ingest/jobs/{job_id}")
async def get_job(job_id: UUID, _: Staff, session: Session, state: State) -> JobOut:
    return job_out(await ingest.get_job(session, job_id), state.store)


@router.post("/ingest/jobs/{job_id}/retry")
async def retry_job(
    job_id: UUID, user: Inspector, state: State, service: Ingestion, request: Request
) -> JobOut:
    job = await service.retry(job_id)
    async with state.unit_of_work() as session:
        await _audit(session, request, user.id, "ingest.retry", job_id)
    return job_out(job, state.store)


@router.post("/ingest/jobs/{job_id}/facade")
async def assign_facade(
    job_id: UUID, body: FacadeChoiceIn, user: Inspector, state: State, service: Ingestion, request: Request
) -> JobOut:
    job = await service.assign_facade(job_id, body.facade_id)
    async with state.unit_of_work() as session:
        await _audit(
            session, request, user.id, "ingest.assign_facade", job_id, {"facade": str(body.facade_id)}
        )
    return job_out(job, state.store)


@router.post("/ingest/uploads", status_code=202)
async def upload_photos(
    user: Inspector,
    state: State,
    service: Ingestion,
    request: Request,
    files: Annotated[list[UploadFile], File()],
    site_id: Annotated[UUID | None, Form()] = None,
    facade_id: Annotated[UUID | None, Form()] = None,
    device_id: Annotated[UUID | None, Form()] = None,
) -> BatchOut:
    if len(files) > ingest.MAX_BATCH_FILES:
        raise SaduError("batch_size", status=422, max_files=ingest.MAX_BATCH_FILES)
    state.rate_limiter.check(f"uploads:{user.id}", UPLOAD_BATCHES_PER_USER_PER_HOUR, 3600)
    photos = [
        ingest.UploadedPhoto(_file_name(file), await file.read(capture.MAX_UPLOAD_BYTES + 1))
        for file in files
    ]
    target = ingest.UploadTarget(site_id=site_id, facade_id=facade_id, device_id=device_id)
    batch_id = await service.queue_uploads(photos, target, user.id)
    async with state.unit_of_work() as session:
        await _audit(session, request, user.id, "ingest.upload", batch_id, {"files": len(photos)})
        views = await ingest.list_jobs(session, batch_id=batch_id, limit=ingest.MAX_BATCH_FILES)
    return batch_out(batch_id, views, state.store)


@router.get("/ingest/batches/{batch_id}")
async def get_batch(batch_id: UUID, _: Staff, session: Session, state: State) -> BatchOut:
    views = await ingest.list_jobs(session, batch_id=batch_id, limit=ingest.MAX_BATCH_FILES)
    if not views:
        raise NotFound("not_found")
    return batch_out(batch_id, views, state.store)


@router.get("/ingest/demo-snapshots/{name}", dependencies=[Depends(public)])
async def demo_snapshot(name: str, state: State) -> Response:
    settings = state.settings
    if not settings.sadu_demo_mode or not DEMO_SNAPSHOT_NAME.fullmatch(name):
        raise NotFound("not_found")
    path = Path(settings.sadu_region_packs_dir) / "demo" / "test-photos" / name
    if not path.is_file():
        raise NotFound("not_found")
    return Response(path.read_bytes(), media_type="image/jpeg")


def _file_name(file: UploadFile) -> str:
    return PurePath(file.filename or "").name.strip() or DEFAULT_FILE_NAME


async def _audit(
    session: AsyncSession,
    request: Request,
    actor_id: UUID,
    action: str,
    target_id: UUID,
    details: dict[str, Any] | None = None,
) -> None:
    await admin.audit(
        session,
        actor_id=actor_id,
        action=action,
        target_type=action.split(".", 1)[0],
        target_id=str(target_id),
        details=details,
        request_id=getattr(request.state, "request_id", None),
    )
