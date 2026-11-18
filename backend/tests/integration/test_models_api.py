import io
import json
import zipfile

import pytest

from sadu.modules.admin import api as admin
from sadu.shared.vocabulary import DamageType, Severity
from tests.integration.test_maps_api import (
    LONG_TEST_PHRASE,
    client,
    create_map,
    detector,
    login,
    north_facade_id,
)

__all__ = ["client", "detector"]

ENGINEER = "ml@example.org"


@pytest.fixture
async def engineer(committed_unit_of_work) -> str:
    async with committed_unit_of_work() as session:
        await admin.create_user(session, ENGINEER, LONG_TEST_PHRASE, admin.Role.ML_ENGINEER)
    return ENGINEER


def candidate(version: str) -> dict:
    return {
        "name": f"athar-damage-v{version}",
        "version": version,
        "base_model": "unsloth/Qwen3.5-4B",
        "adapter_uri": f"hf://athar/athar-damage-lora@v{version}",
        "metrics": {"json_valid_rate": 0.97, "macro_f1": 0.41},
    }


async def test_model_engineer_registers_and_activates_one_model_at_a_time(client, engineer):
    inspector = await login(client, "inspector@example.org")
    assert (await client.get("/ml/models")).status_code == 403
    assert (await client.post("/ml/models", json=candidate("1"), headers=inspector)).status_code == 403

    headers = await login(client, engineer)
    first = await client.post("/ml/models", json=candidate("1"), headers=headers)
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "candidate"
    second = (await client.post("/ml/models", json=candidate("2"), headers=headers)).json()
    duplicate = await client.post("/ml/models", json=candidate("2"), headers=headers)
    assert duplicate.status_code == 409 and duplicate.json()["code"] == "model_version_exists"

    activated = await client.post(f"/ml/models/{first.json()['id']}/activate", headers=headers)
    assert activated.json()["status"] == "active" and activated.json()["activated_at"]
    await client.post(f"/ml/models/{second['id']}/activate", headers=headers)
    statuses = {m["version"]: m["status"] for m in (await client.get("/ml/models")).json()}
    assert statuses == {"1": "retired", "2": "active"}

    again = await client.post(f"/ml/models/{second['id']}/activate", headers=headers)
    assert again.status_code == 409 and again.json()["code"] == "model_status_unchanged"
    retired = await client.post(f"/ml/models/{second['id']}/retire", headers=headers)
    assert retired.json()["status"] == "retired"


async def test_training_export_holds_only_approved_maps_without_people(client, detector, engineer):
    detector.cells = [
        ("A1", DamageType.CRACK, Severity.MODERATE),
        ("H3", DamageType.PLASTER_LOSS, Severity.WATCH),
    ]
    expert = await login(client, "expert@example.org")
    facade_id = await north_facade_id(client)
    approved = (await create_map(client, expert, {"facade_id": facade_id})).json()
    await create_map(client, expert, {"facade_id": facade_id})
    await client.post(f"/maps/{approved['id']}/field-inspection", json={"notes": "زيارة"}, headers=expert)
    assert (await client.post(f"/maps/{approved['id']}/approve", headers=expert)).status_code == 200

    assert (await client.get("/ml/training-export")).status_code == 403
    await login(client, engineer)
    response = await client.get("/ml/training-export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    [record] = [json.loads(line) for line in archive.read("manifest.jsonl").decode().splitlines()]
    assert record["map_id"] == approved["id"] and record["label_quality"] == "expert"
    assert record["image"] in archive.namelist()
    assert archive.read(record["image"]).startswith(b"\xff\xd8")
    assert {e["damage_type"] for e in record["elements"]} == {"crack", "plaster_loss"}
    assert (record["rows"], record["cols"], record["detector"]) == (8, 13, "scripted")
    assert not {"created_by", "approved_by", "field_notes", "wall_name"} & record.keys()
    assert json.loads(archive.read("export.json"))["examples"] == 1

    with_weak = zipfile.ZipFile(io.BytesIO((await client.get("/ml/training-export?weak=true")).content))
    qualities = [json.loads(line)["label_quality"] for line in with_weak.read("manifest.jsonl").splitlines()]
    assert qualities == ["expert", "weak"]
