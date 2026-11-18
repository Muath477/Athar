import io
import json

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from PIL import ExifTags, Image

from sadu.main import create_app
from sadu.modules.admin import api as admin
from sadu.modules.agents import api as agents
from sadu.modules.agents.api import AgentRunner, Dependencies
from sadu.modules.ingest import api as ingest
from sadu.shared.adapters.azure_speech import NoSpeech
from sadu.shared.config import get_settings
from sadu.shared.web import AppState
from tests.fakes import FakeLLM
from tests.integration.conftest import PACK_DIR
from tests.integration.test_maps_api import LONG_TEST_PHRASE, PHOTO, ScriptedDetector, login

DEMO_SITE_LAT, DEMO_SITE_LON = 24.7136, 46.6753
METRES_PER_LAT_DEGREE = 111_195
CREDENTIAL_ENV = "SADU_CAMERA_SECRET_GATE"


class FakeCameras:
    def __init__(self) -> None:
        self.photo = PHOTO
        self.error: ingest.CameraUnreachable | None = None
        self.targets: list[ingest.CameraTarget] = []

    async def snapshot(self, target: ingest.CameraTarget) -> bytes:
        self.targets.append(target)
        if self.error is not None:
            raise self.error
        return self.photo


@pytest.fixture
def cameras() -> FakeCameras:
    return FakeCameras()


@pytest.fixture
async def ingestion(committed_unit_of_work, store, cameras) -> ingest.Ingestion:
    return ingest.Ingestion(committed_unit_of_work, store, ScriptedDetector(), cameras, map_rows=8)


@pytest.fixture
async def client(committed_unit_of_work, store, ingestion):
    unit_of_work = committed_unit_of_work
    async with unit_of_work() as session:
        await agents.seed_region_pack(session, store, PACK_DIR)
        for email, role in (
            ("manager@example.org", admin.Role.SITE_MANAGER),
            ("inspector@example.org", admin.Role.INSPECTOR),
            ("authority@example.org", admin.Role.AUTHORITY),
        ):
            await admin.create_user(session, email, LONG_TEST_PHRASE, role)
    deps = Dependencies(unit_of_work=unit_of_work, store=store, llm=FakeLLM(), tts=NoSpeech())
    app = create_app()
    app.state.sadu = AppState(
        settings=get_settings(),
        unit_of_work=unit_of_work,
        store=store,
        runner=AgentRunner(deps, InMemorySaver(), max_concurrent=1),
    )
    app.state.ingestion = ingestion
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as http:
        yield http


async def demo_site(client: httpx.AsyncClient) -> dict:
    [site] = [s for s in (await client.get("/sites")).json() if s["slug"] == "demo-house"]
    return site


async def facade_id(client: httpx.AsyncClient, code: str) -> str:
    return next(f["id"] for f in (await demo_site(client))["facades"] if f["code"] == code)


async def add_camera(client: httpx.AsyncClient, headers: dict[str, str], **fields: object) -> dict:
    site = await demo_site(client)
    body = {
        "kind": "fixed_camera",
        "name_ar": "كاميرا البوابة",
        "site_id": site["id"],
        "facade_id": await facade_id(client, "north"),
        "snapshot_url": "http://camera.example/ISAPI/picture",
        "username": "viewer",
        "secret_env": CREDENTIAL_ENV,
        **fields,
    }
    response = await client.post("/ingest/devices", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def photo_taken_at(north_m: float) -> bytes:
    lat = DEMO_SITE_LAT + north_m / METRES_PER_LAT_DEGREE

    def dms(value: float) -> tuple[float, float, float]:
        degrees = int(value)
        minutes = int((value - degrees) * 60)
        return (float(degrees), float(minutes), round(((value - degrees) * 60 - minutes) * 60, 4))

    exif = Image.Exif()
    exif.get_ifd(ExifTags.IFD.GPSInfo).update(
        {
            ExifTags.GPS.GPSLatitudeRef: "N",
            ExifTags.GPS.GPSLatitude: dms(lat),
            ExifTags.GPS.GPSLongitudeRef: "E",
            ExifTags.GPS.GPSLongitude: dms(DEMO_SITE_LON),
        }
    )
    exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = "2026:11:12 07:45:00"
    buffer = io.BytesIO()
    Image.open(io.BytesIO(PHOTO)).save(buffer, "JPEG", exif=exif, quality=90)
    return buffer.getvalue()


async def upload(client: httpx.AsyncClient, headers: dict[str, str], photos: list[bytes], **form: str):
    files = [("files", (f"wall-{i}.jpg", photo, "image/jpeg")) for i, photo in enumerate(photos)]
    return await client.post("/ingest/uploads", headers=headers, files=files, data=form)


async def test_only_device_managers_change_the_registry_and_secrets_stay_out(client):
    inspector = await login(client, "inspector@example.org")
    denied = await client.post(
        "/ingest/devices", headers=inspector, json={"kind": "drone", "name_ar": "طائرة المسح"}
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "forbidden"

    manager = await login(client, "manager@example.org")
    camera = await add_camera(client, manager)
    assert camera["secret_env"] == CREDENTIAL_ENV
    assert camera["secret_configured"] is False
    assert camera["last_status"] is None
    assert "password" not in json.dumps(camera).lower()

    with_password = await client.post(
        "/ingest/devices",
        headers=manager,
        json={
            **{k: camera[k] for k in ("kind", "name_ar", "site_id")},
            "snapshot_url": "http://a:b@cam.example/s",
        },
    )
    assert with_password.status_code == 422
    assert with_password.json()["code"] == "invalid_camera_url"

    raw_secret = await client.post(
        "/ingest/devices",
        headers=manager,
        json={"kind": "drone", "name_ar": "طائرة", "secret_env": "hunter2"},
    )
    assert raw_secret.status_code == 422

    renamed = await client.post(
        f"/ingest/devices/{camera['id']}",
        headers=manager,
        json={
            **{k: camera[k] for k in ("kind", "site_id", "facade_id", "snapshot_url")},
            "name_ar": "كاميرا الشمال",
        },
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name_ar"] == "كاميرا الشمال"

    authority = await login(client, "authority@example.org")
    listed = await client.get("/ingest/devices")
    assert [d["name_ar"] for d in listed.json()] == ["كاميرا الشمال"]
    refused = await client.delete(f"/ingest/devices/{camera['id']}", headers=authority)
    assert refused.status_code == 403
    assert refused.json()["code"] == "forbidden"

    manager = await login(client, "manager@example.org")
    assert (await client.delete(f"/ingest/devices/{camera['id']}", headers=manager)).status_code == 204
    assert (await client.get("/ingest/devices")).json() == []


async def test_capture_now_queues_a_job_that_becomes_a_draft_camera_map(
    client, ingestion, cameras, monkeypatch
):
    monkeypatch.setenv(CREDENTIAL_ENV, "s3cret")
    manager = await login(client, "manager@example.org")
    camera = await add_camera(client, manager)
    assert camera["secret_configured"] is True

    captured = await client.post(f"/ingest/devices/{camera['id']}/capture", headers=manager)
    assert captured.status_code == 202, captured.text
    assert captured.json()["status"] == "queued"
    assert cameras.targets == [
        ingest.CameraTarget("http://camera.example/ISAPI/picture", None, "viewer", "s3cret")
    ]

    await ingestion.join()
    job = (await client.get(f"/ingest/jobs/{captured.json()['id']}")).json()
    assert job["status"] == "done", job
    assert job["source"] == "camera" and job["facade_match"] == "device"
    assert job["photo_url"] is not None

    created = (await client.get(f"/maps/{job['map_id']}")).json()
    assert created["status"] == "draft"
    assert created["facade_id"] == camera["facade_id"]
    assert (created["source"], created["source_label"]) == ("camera", "كاميرا البوابة")

    device = (await client.get(f"/ingest/devices/{camera['id']}")).json()
    assert device["last_status"] == "ok" and device["thumbnail_url"] is not None
    history = (await client.get("/ingest/jobs", params={"device_id": camera["id"]})).json()
    assert [h["id"] for h in history] == [job["id"]]


async def test_unreachable_camera_is_recorded_without_a_retry(client, cameras):
    cameras.error = ingest.CameraUnreachable("blocked_address")
    manager = await login(client, "manager@example.org")
    camera = await add_camera(client, manager)

    captured = (await client.post(f"/ingest/devices/{camera['id']}/capture", headers=manager)).json()

    assert captured["status"] == "failed"
    assert "SADU_CAMERA_ALLOWED_HOSTS" in captured["error_ar"]
    assert captured["can_retry"] is False
    device = (await client.get(f"/ingest/devices/{camera['id']}")).json()
    assert device["last_status"] == "failed"
    assert device["last_error_ar"] == captured["error_ar"]


async def test_bulk_upload_of_two_photos_creates_two_upload_maps(client, ingestion):
    inspector = await login(client, "inspector@example.org")
    north = await facade_id(client, "north")

    response = await upload(client, inspector, [PHOTO, PHOTO], facade_id=north)
    assert response.status_code == 202, response.text
    batch = response.json()
    assert batch["total"] == 2 and batch["counts"] == {"queued": 2}

    await ingestion.join()
    batch = (await client.get(f"/ingest/batches/{batch['id']}")).json()
    assert batch["counts"] == {"done": 2}
    assert [job["file_name"] for job in batch["jobs"]] == ["wall-0.jpg", "wall-1.jpg"]
    for job in batch["jobs"]:
        created = (await client.get(f"/maps/{job['map_id']}")).json()
        assert created["facade_id"] == north
        assert (created["source"], created["source_label"]) == ("upload", None)


async def test_photo_without_location_waits_for_a_person_to_pick_the_facade(client, ingestion):
    inspector = await login(client, "inspector@example.org")
    [job] = (await upload(client, inspector, [PHOTO])).json()["jobs"]

    await ingestion.join()
    waiting = (await client.get(f"/ingest/jobs/{job['id']}")).json()
    assert waiting["status"] == "needs_facade"
    assert waiting["map_id"] is None

    east = await facade_id(client, "east")
    assigned = await client.post(
        f"/ingest/jobs/{job['id']}/facade", headers=inspector, json={"facade_id": east}
    )
    assert assigned.status_code == 200, assigned.text
    await ingestion.join()
    done = (await client.get(f"/ingest/jobs/{job['id']}")).json()
    assert done["status"] == "done" and done["facade_id"] == east and done["facade_match"] == "chosen"


async def test_drone_photo_with_gps_finds_its_facade(client, ingestion):
    manager = await login(client, "manager@example.org")
    drone = await client.post(
        "/ingest/devices", headers=manager, json={"kind": "drone", "name_ar": "درون المسح"}
    )
    assert drone.status_code == 201, drone.text

    inspector = await login(client, "inspector@example.org")
    response = await upload(client, inspector, [photo_taken_at(north_m=18)], device_id=drone.json()["id"])
    await ingestion.join()

    [job] = (await client.get(f"/ingest/batches/{response.json()['id']}")).json()["jobs"]
    assert job["status"] == "done", job
    assert job["facade_match"] == "gps"
    assert job["facade_id"] == await facade_id(client, "north")
    assert job["lat"] == pytest.approx(DEMO_SITE_LAT + 18 / METRES_PER_LAT_DEGREE, abs=1e-5)
    assert job["taken_at"] == "2026-11-12T07:45:00"
    created = (await client.get(f"/maps/{job['map_id']}")).json()
    assert (created["source"], created["source_label"]) == ("drone", "درون المسح")


async def test_far_away_gps_is_left_for_a_person(client, ingestion):
    inspector = await login(client, "inspector@example.org")
    response = await upload(client, inspector, [photo_taken_at(north_m=500)])
    await ingestion.join()

    [job] = (await client.get(f"/ingest/batches/{response.json()['id']}")).json()["jobs"]
    assert job["status"] == "needs_facade"
    assert job["facade_match"] is None


async def test_upload_limits_are_enforced(client):
    inspector = await login(client, "inspector@example.org")

    too_many = await upload(client, inspector, [b"x"] * 31)
    assert too_many.status_code == 422

    heic = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic"
    rejected = await client.post(
        "/ingest/uploads", headers=inspector, files=[("files", ("IMG_0001.HEIC", heic, "image/heic"))]
    )
    assert rejected.status_code == 415
    assert "IMG_0001.HEIC" in rejected.json()["detail"]

    authority = await login(client, "authority@example.org")
    refused = await upload(client, authority, [PHOTO])
    assert refused.status_code == 403
    assert refused.json()["code"] == "forbidden"


async def test_failed_upload_can_be_retried(client, ingestion):
    inspector = await login(client, "inspector@example.org")
    north = await facade_id(client, "north")
    [job] = (await upload(client, inspector, [b"not an image"], facade_id=north)).json()["jobs"]

    await ingestion.join()
    failed = (await client.get(f"/ingest/jobs/{job['id']}")).json()
    assert failed["status"] == "failed"
    assert failed["error_ar"] == "أرسل صورة بصيغة JPEG أو PNG."
    assert failed["can_retry"] is True

    retried = await client.post(f"/ingest/jobs/{job['id']}/retry", headers=inspector)
    assert retried.status_code == 200
    assert retried.json()["status"] == "queued"
    await ingestion.join()
    assert (await client.get(f"/ingest/jobs/{job['id']}")).json()["attempts"] == 1
