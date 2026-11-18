import json
import re
import zlib

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from sadu.main import create_app
from sadu.modules.admin import api as admin
from sadu.modules.agents import api as agents
from sadu.modules.agents.api import AgentRunner, Dependencies
from sadu.modules.mapping.application.ports import DetectionInput, DetectionOutput, DetectorUnavailable
from sadu.modules.mapping.domain.damage_map import CellSource, MapCell
from sadu.shared.adapters.azure_speech import NoSpeech
from sadu.shared.config import get_settings
from sadu.shared.vocabulary import DamageType, ModelConfidence, RetakeReason, Severity
from sadu.shared.web import AppState
from tests.fakes import FakeLLM
from tests.integration.conftest import PACK_DIR

PHOTO = (PACK_DIR / "test-photos" / "north-crack.jpg").read_bytes()
LONG_TEST_PHRASE = "a long test password"


class ScriptedDetector:
    def __init__(self) -> None:
        self.cells: list[tuple[str, DamageType, Severity]] = []
        self.usable = True
        self.down = False

    @property
    def name(self) -> str:
        return "scripted"

    async def detect(self, request: DetectionInput) -> DetectionOutput:
        if self.down:
            raise DetectorUnavailable("scripted outage")
        if not self.usable:
            return DetectionOutput(cells=(), usable=False, retake_reason=RetakeReason.BLURRY)
        cells = tuple(
            MapCell(
                request.grid.parse(label), damage_type, severity, ModelConfidence.MEDIUM, CellSource.MODEL
            )
            for label, damage_type, severity in self.cells
        )
        return DetectionOutput(cells=cells, summary_ar="ملخص تجريبي.")


@pytest.fixture
def detector() -> ScriptedDetector:
    return ScriptedDetector()


@pytest.fixture
async def client(committed_unit_of_work, store, detector):
    unit_of_work = committed_unit_of_work
    async with unit_of_work() as session:
        await agents.seed_region_pack(session, store, PACK_DIR)
        await admin.create_user(session, "expert@example.org", LONG_TEST_PHRASE, admin.Role.EXPERT)
        await admin.create_user(session, "inspector@example.org", LONG_TEST_PHRASE, admin.Role.INSPECTOR)
    deps = Dependencies(unit_of_work=unit_of_work, store=store, llm=FakeLLM(), tts=NoSpeech())
    app = create_app()
    app.state.sadu = AppState(
        settings=get_settings(),
        unit_of_work=unit_of_work,
        store=store,
        runner=AgentRunner(deps, InMemorySaver(), max_concurrent=1),
    )
    app.state.damage_detector = detector
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as http:
        yield http


def pdf_objects(pdf: bytes) -> bytes:
    unpacked = [pdf]
    for stream in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.DOTALL):
        try:
            unpacked.append(zlib.decompress(stream))
        except zlib.error:
            continue
    return b"".join(unpacked)


async def login(client: httpx.AsyncClient, email: str) -> dict[str, str]:
    response = await client.post("/auth/login", json={"email": email, "password": LONG_TEST_PHRASE})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def north_facade_id(client: httpx.AsyncClient) -> str:
    [site] = (await client.get("/sites")).json()
    return next(f["id"] for f in site["facades"] if f["code"] == "north")


async def create_map(client: httpx.AsyncClient, headers: dict[str, str], meta: dict) -> httpx.Response:
    return await client.post(
        "/maps",
        headers=headers,
        files={"photo": ("wall.jpg", PHOTO, "image/jpeg")},
        data={"meta": json.dumps(meta)},
    )


async def test_inspector_maps_a_wall_and_expert_corrects_and_approves_it(client, detector):
    detector.cells = [
        ("A1", DamageType.CRACK, Severity.MODERATE),
        ("H3", DamageType.PLASTER_LOSS, Severity.WATCH),
    ]
    inspector = await login(client, "inspector@example.org")
    facade_id = await north_facade_id(client)
    corners = [[0.05, 0.05], [0.95, 0.05], [0.95, 0.95], [0.05, 0.95]]

    created = await create_map(client, inspector, {"facade_id": facade_id, "corners": corners})
    assert created.status_code == 201, created.text
    body = created.json()
    assert (body["rows"], body["cols"], body["width_m"], body["height_m"]) == (8, 13, 10.0, 6.0)
    assert body["status"] == "draft" and body["detector_status"] == "ok"
    assert [c["cell"] for c in body["cells"]] == ["A1", "H3"]
    plan_codes = [item["code"] for item in body["treatment_plan"]["items"]]
    assert plan_codes == ["crack-fill", "plaster-renew"]
    assert body["treatment_plan"]["review_status"] == "draft"
    assert body["changes"] is None

    correction = {
        "corrections": [{"cell": "A1", "damage_type": "none"}, {"cell": "B2", "damage_type": "moisture"}]
    }
    assert (
        await client.post(f"/maps/{body['id']}/cells", json=correction, headers=inspector)
    ).status_code == 403

    expert = await login(client, "expert@example.org")
    corrected = await client.post(f"/maps/{body['id']}/cells", json=correction, headers=expert)
    assert corrected.status_code == 200, corrected.text
    assert [(c["cell"], c["source"]) for c in corrected.json()["cells"]] == [
        ("B2", "expert"),
        ("H3", "model"),
    ]

    approved = await client.post(f"/maps/{body['id']}/approve", headers=expert)
    assert approved.json()["status"] == "approved"
    again = await client.post(f"/maps/{body['id']}/cells", json=correction, headers=expert)
    assert again.status_code == 409

    accuracy = (await client.get("/maps/accuracy")).json()
    by_type = {s["damage_type"]: s for s in accuracy["by_type"]}
    assert accuracy["maps"] == 1
    assert by_type["crack"]["false_positives"] == 1
    assert by_type["plaster_loss"]["true_positives"] == 1
    assert by_type["moisture"]["false_negatives"] == 1

    detector.cells = [("B2", DamageType.MOISTURE, Severity.URGENT), ("C5", DamageType.CRACK, Severity.WATCH)]
    second_response = await create_map(client, expert, {"facade_id": facade_id})
    assert second_response.status_code == 201, second_response.text
    second = second_response.json()
    changes = second["changes"]
    assert changes["previous_map_id"] == body["id"] and changes["comparable"]
    assert {(c["cell"], c["kind"]) for c in changes["items"]} == {
        ("B2", "worse"),
        ("C5", "new"),
        ("H3", "resolved"),
    }

    listed = (await client.get("/maps", params={"facade_id": facade_id})).json()
    assert [m["id"] for m in listed] == [second["id"], body["id"]]
    assert listed[1]["damaged_cells"] == 2
    assert listed[0]["urgent_cells"] == 1
    assert listed[0]["thumbnail_url"].startswith("memory://maps/rectified/")


async def test_unregistered_wall_needs_a_name_and_size(client):
    inspector = await login(client, "inspector@example.org")
    missing = await create_map(client, inspector, {"wall_name": "جدار السوق"})
    assert missing.status_code == 422
    assert missing.json()["code"] == "wall_size_required"

    created = await create_map(client, inspector, {"wall_name": "جدار السوق", "width_m": 4, "height_m": 3})
    assert created.status_code == 201
    assert created.json()["cols"] == 11


async def test_bad_corners_and_unusable_photos_are_rejected(client, detector):
    inspector = await login(client, "inspector@example.org")
    facade_id = await north_facade_id(client)
    crossed = [[0, 0], [1, 1], [1, 0], [0, 1]]
    bad = await create_map(client, inspector, {"facade_id": facade_id, "corners": crossed})
    assert bad.json()["code"] == "invalid_corners"

    detector.usable = False
    blurry = await create_map(client, inspector, {"facade_id": facade_id})
    assert blurry.status_code == 422
    assert blurry.json()["code"] == "photo_unusable"
    assert "واضحة" in blurry.json()["detail"]


async def test_detector_outage_still_creates_a_map_for_manual_labelling(client, detector):
    detector.down = True
    inspector = await login(client, "inspector@example.org")
    created = await create_map(client, inspector, {"facade_id": await north_facade_id(client)})
    assert created.status_code == 201
    assert created.json()["detector_status"] == "failed"
    assert created.json()["cells"] == []


async def test_treatment_catalog_is_readable_by_inspectors(client):
    assert (await client.get("/treatments/catalog")).status_code == 401
    await login(client, "inspector@example.org")
    catalog = (await client.get("/treatments/catalog")).json()
    assert catalog["review_status"] == "draft"
    assert all(t["sources"] for t in catalog["treatments"])


async def test_wall_report_pdf_is_for_staff_and_embeds_an_arabic_font(client, detector):
    detector.cells = [("A1", DamageType.CRACK, Severity.URGENT), ("C4", DamageType.MOISTURE, Severity.WATCH)]
    inspector = await login(client, "inspector@example.org")
    created = await create_map(client, inspector, {"facade_id": await north_facade_id(client)})
    map_id = created.json()["id"]

    response = await client.get(f"/maps/{map_id}/report.pdf")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith('attachment; filename="athar-wall-report-')
    assert response.content.startswith(b"%PDF-")
    assert b"Noto-Naskh-Arabic" in pdf_objects(response.content)

    client.cookies.clear()
    assert (await client.get(f"/maps/{map_id}/report.pdf")).status_code == 401
