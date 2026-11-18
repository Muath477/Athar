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


@pytest.fixture
async def site_manager(committed_unit_of_work) -> str:
    async with committed_unit_of_work() as session:
        await admin.create_user(session, "manager@example.org", LONG_TEST_PHRASE, admin.Role.SITE_MANAGER)
    return "manager@example.org"


async def test_each_role_gets_only_its_own_permissions(client, site_manager):
    manager = await login(client, site_manager)
    me = (await client.get("/auth/me")).json()
    assert me["role"] == "site_manager"
    assert me["permissions"] == ["assistant", "export", "manage_devices", "manage_site", "read"]
    roles = {r["role"]: r["permissions"] for r in (await client.get("/auth/roles")).json()}
    assert roles["inspector"] == ["assistant", "read", "survey"]
    assert roles["expert"] == ["assistant", "export", "read", "review", "survey"]
    assert roles["authority"] == ["assistant", "export", "read"]
    assert roles["ml_engineer"] == ["export", "manage_models", "read"]

    [site] = (await client.get("/sites")).json()
    assert (await client.get(f"/sites/{site['id']}/condition")).status_code == 200
    facade_id = site["facades"][0]["id"]
    assert (await create_map(client, manager, {"facade_id": facade_id})).status_code == 403
    closed = await client.post(
        f"/sites/{site['id']}/field-photography", json={"permitted": False}, headers=manager
    )
    assert closed.status_code == 200 and closed.json()["field_photography_permitted"] is False

    inspector = await login(client, "inspector@example.org")
    reopen = await client.post(
        f"/sites/{site['id']}/field-photography", json={"permitted": True}, headers=inspector
    )
    assert reopen.status_code == 403


async def test_visitor_missions_need_the_sites_photography_permit(client, site_manager):
    expert = await login(client, "expert@example.org")
    facade_id = await north_facade_id(client)
    [site] = (await client.get("/sites")).json()
    opened = await client.post("/missions", json={"facade_id": facade_id}, headers=expert)
    assert opened.status_code == 201, opened.text

    manager = await login(client, site_manager)
    await client.post(f"/sites/{site['id']}/field-photography", json={"permitted": False}, headers=manager)
    other = site["facades"][1]["id"]
    expert = await login(client, "expert@example.org")
    refused = await client.post("/missions", json={"facade_id": other}, headers=expert)
    assert refused.status_code == 409 and refused.json()["code"] == "field_photography_not_permitted"

    nearby = await client.get("/missions/nearby?lat=24.7136&lon=46.6753")
    assert nearby.status_code == 200 and nearby.json() == []


async def test_site_condition_summarises_every_wall_for_the_manager(client, detector, site_manager):
    detector.cells = [
        ("H1", DamageType.BASAL_EROSION, Severity.URGENT),
        ("B2", DamageType.CRACK, Severity.WATCH),
    ]
    inspector = await login(client, "inspector@example.org")
    facade_id = await north_facade_id(client)
    created = await create_map(client, inspector, {"facade_id": facade_id})
    assert created.status_code == 201

    await login(client, site_manager)
    [site] = (await client.get("/sites")).json()
    condition = (await client.get(f"/sites/{site['id']}/condition")).json()
    walls = {w["facade_id"]: w for w in condition["walls"]}
    assert len(walls) == len(site["facades"])
    north = walls[facade_id]
    assert north["status"] == "draft" and north["urgent"] == 1 and north["elements"] == 2
    assert condition["urgent"] == 0 and condition["awaiting_approval"] == 1
    assert {w["status"] for fid, w in walls.items() if fid != facade_id} == {"not_surveyed"}
    assert condition["walls_due"] == len(site["facades"]) - 1
    assert condition["totals"] == [] and condition["materials"] == []
