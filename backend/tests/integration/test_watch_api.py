import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from sadu.main import create_app
from sadu.modules.admin import api as admin
from sadu.modules.agents import api as agents
from sadu.modules.agents.api import AgentRunner, Dependencies
from sadu.modules.watch.infrastructure.disabled_source import DisabledSceneSource
from sadu.modules.watch.infrastructure.sample_source import SampleSceneSource
from sadu.shared.adapters.azure_speech import NoSpeech
from sadu.shared.config import get_settings
from sadu.shared.web import AppState
from tests.fakes import FakeLLM
from tests.integration.conftest import PACK_DIR

LONG_TEST_PHRASE = "a long test password"


@pytest.fixture
def events(tmp_path):
    path = tmp_path / "sample-events.json"
    starts = (datetime.now(UTC).date() - timedelta(days=25)).isoformat()
    flood = {"threat": "water", "starts": starts, "east_m": 0, "north_m": 0, "size_m": 40}
    path.write_text(json.dumps({"events": {"demo-house": [flood]}}), encoding="utf-8")
    return path


@pytest.fixture
async def app(committed_unit_of_work, store, events):
    unit_of_work = committed_unit_of_work
    async with unit_of_work() as session:
        await agents.seed_region_pack(session, store, PACK_DIR)
        await admin.create_user(session, "expert@example.org", LONG_TEST_PHRASE, admin.Role.EXPERT)
        await admin.create_user(session, "inspector@example.org", LONG_TEST_PHRASE, admin.Role.INSPECTOR)
    deps = Dependencies(unit_of_work=unit_of_work, store=store, llm=FakeLLM(), tts=NoSpeech())
    application = create_app()
    application.state.sadu = AppState(
        settings=get_settings(),
        unit_of_work=unit_of_work,
        store=store,
        runner=AgentRunner(deps, InMemorySaver(), max_concurrent=1),
    )
    application.state.scene_source = SampleSceneSource(events)
    return application


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as http:
        yield http


async def login(client: httpx.AsyncClient, email: str) -> dict[str, str]:
    response = await client.post("/auth/login", json={"email": email, "password": LONG_TEST_PHRASE})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def test_satellite_alert_turns_into_ground_missions(client, store):
    assert (await client.get("/watch/sites")).status_code == 401
    headers = await login(client, "inspector@example.org")

    overview = (await client.get("/watch/sites")).json()
    assert overview["source"] == "sample" and overview["is_sample"] is True
    [site] = overview["sites"]
    assert site["latest"] is None and site["facades"] > 0

    scan = await client.post(f"/watch/sites/{site['site_id']}/scans", headers=headers)
    assert scan.status_code == 201, scan.text
    body = scan.json()
    assert body["status"] == "ok" and body["is_sample"] is True
    assert body["level"] in {"watch", "moderate", "urgent"}
    assert {(s["threat"], s["zone"]) for s in body["signals"]} >= {("water", "inside")}
    assert all(body[key] for key in ("before_url", "after_url", "change_url"))
    assert len([key for key in store.objects if key.startswith("watch/")]) == 3

    ranked = (await client.get("/watch/sites")).json()["sites"]
    assert ranked[0]["latest"]["id"] == body["id"] and ranked[0]["priority"] > 0

    check = await client.post(f"/watch/scans/{body['id']}/ground-check", headers=headers)
    assert check.status_code == 200, check.text
    result = check.json()
    assert result["mission_ids"] and result["inspector_visit"] is False
    missions = (await client.get("/missions")).json()
    assert {m["reason"] for m in missions} >= {"satellite_alert"}

    history = (await client.get(f"/watch/sites/{site['site_id']}/scans")).json()
    assert [h["id"] for h in history] == [body["id"]]
    assert history[0]["ground_check_at"] is not None


async def test_only_experts_acknowledge_alerts(client):
    headers = await login(client, "inspector@example.org")
    [site] = (await client.get("/watch/sites")).json()["sites"]
    scan = (await client.post(f"/watch/sites/{site['site_id']}/scans", headers=headers)).json()
    assert (await client.post(f"/watch/scans/{scan['id']}/acknowledge", headers=headers)).status_code == 403

    await client.post("/auth/logout", headers=headers)
    expert = await login(client, "expert@example.org")
    acknowledged = await client.post(f"/watch/scans/{scan['id']}/acknowledge", headers=expert)
    assert acknowledged.status_code == 200 and acknowledged.json()["acknowledged_at"] is not None


async def test_a_disabled_source_records_that_no_verdict_was_possible(app, client):
    app.state.scene_source = DisabledSceneSource()
    headers = await login(client, "inspector@example.org")
    [site] = (await client.get("/watch/sites")).json()["sites"]
    scan = (await client.post(f"/watch/sites/{site['site_id']}/scans", headers=headers)).json()
    assert scan["status"] == "source_unavailable" and scan["level"] == "unknown"
    assert scan["signals"] == [] and scan["before_url"] is None
