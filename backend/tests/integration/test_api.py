import json

import httpx
import pytest
from fastapi.routing import APIRoute
from langgraph.checkpoint.memory import InMemorySaver

from sadu.main import create_app
from sadu.modules.admin import api as admin
from sadu.modules.agents import api as agents
from sadu.modules.agents.api import AgentRunner, Dependencies
from sadu.shared.adapters.azure_speech import NoSpeech
from sadu.shared.config import get_settings
from sadu.shared.web import AppState
from tests.fakes import FakeLLM
from tests.integration.conftest import PACK_DIR
from tests.integration.test_observation_run import scripted_model

ACCESS_DEPENDENCIES = {"public", "require_inspector", "require_expert", "require_admin", "required_passport"}


@pytest.fixture
async def client(committed_unit_of_work, store):
    unit_of_work = committed_unit_of_work
    async with unit_of_work() as session:
        await agents.seed_region_pack(session, store, PACK_DIR)
    deps = Dependencies(unit_of_work=unit_of_work, store=store, llm=FakeLLM(scripted_model()), tts=NoSpeech())
    runner = AgentRunner(deps, InMemorySaver(), max_concurrent=1)
    app = create_app()
    app.state.sadu = AppState(settings=get_settings(), unit_of_work=unit_of_work, store=store, runner=runner)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as http:
        http.runner = runner
        yield http


def test_every_route_declares_who_may_call_it():
    def names(dependant):
        for dependency in dependant.dependencies:
            yield getattr(dependency.call, "__name__", "")
            yield from names(dependency)

    unguarded = [
        route.path
        for route in create_app().routes
        if isinstance(route, APIRoute) and not ACCESS_DEPENDENCIES & set(names(route.dependant))
    ]
    assert unguarded == []


async def test_visitor_flow_from_upload_to_passport_stamp(client):
    token = (await client.post("/passports")).json()["token"]
    headers = {"X-Passport-Token": token, "Idempotency-Key": "visitor-flow-1"}
    meta = {
        "captured_at": "2026-11-16T10:00:00Z",
        "lat": 24.7136,
        "lon": 46.6753,
        "consent": {"location": True},
    }
    photo = (PACK_DIR / "test-photos" / "north-crack.jpg").read_bytes()

    accepted = await client.post(
        "/observations",
        headers=headers,
        files={"photo": ("p.jpg", photo, "image/jpeg")},
        data={"meta": json.dumps(meta)},
    )
    assert accepted.status_code == 202, accepted.text
    await client.runner.wait()

    observation_id = accepted.json()["observation_id"]
    result = (await client.get(f"/observations/{observation_id}", headers={"X-Passport-Token": token})).json()
    assert result["status"] == "done"
    story = (await client.get(f"/stories/{result['detail']['story_id']}")).json()
    assert story["claims"] and story["claims"][0]["source"]["title"]
    stamps = (await client.get("/passport", headers={"X-Passport-Token": token})).json()["stamps"]
    assert [s["site_name_en"] for s in stamps] == ["Demo mud-brick house"]

    other = (await client.post("/passports")).json()["token"]
    hidden = await client.get(f"/observations/{observation_id}", headers={"X-Passport-Token": other})
    assert hidden.status_code == 403


async def test_location_is_not_kept_without_consent(client):
    meta = {"captured_at": "2026-11-16T10:00:00Z", "lat": 24.7136, "lon": 46.6753}
    photo = (PACK_DIR / "test-photos" / "north-crack.jpg").read_bytes()
    accepted = await client.post(
        "/observations",
        headers={"Idempotency-Key": "no-consent-1"},
        files={"photo": ("p.jpg", photo, "image/jpeg")},
        data={"meta": json.dumps(meta)},
    )
    await client.runner.wait()
    result = (await client.get(f"/observations/{accepted.json()['observation_id']}")).json()
    assert result["detail"] == {"site_found": False}


async def test_dashboard_needs_login_and_csrf(client, committed_unit_of_work):
    async with committed_unit_of_work() as session:
        await admin.create_user(session, "expert@example.org", "a long test password", admin.Role.EXPERT)
    assert (await client.get("/review-queue")).status_code == 401

    login = await client.post(
        "/auth/login", json={"email": "Expert@example.org", "password": "a long test password"}
    )
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]
    assert (await client.get("/review-queue")).status_code == 200

    mission = {"facade_id": "00000000-0000-0000-0000-000000000000"}
    assert (await client.post("/missions", json=mission)).status_code == 403
    assert (await client.post("/missions", json=mission, headers={"X-CSRF-Token": csrf})).status_code == 404
    assert (await client.get("/admin/costs")).status_code == 403


async def test_login_is_rate_limited(client):
    statuses = [
        (await client.post("/auth/login", json={"email": "x@example.org", "password": "wrong"})).status_code
        for _ in range(6)
    ]
    assert statuses == [401] * 5 + [429]


async def test_errors_are_problem_json_with_security_headers(client):
    response = await client.get(
        "/stories/00000000-0000-0000-0000-000000000000", headers={"Accept-Language": "en"}
    )
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "not_found" and response.json()["title"] == "Not found"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "x-request-id" in response.headers
