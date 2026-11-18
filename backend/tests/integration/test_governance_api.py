import csv
import io
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from sadu.modules.admin import api as admin
from sadu.modules.agents import api as agents
from sadu.modules.capture import api as capture
from sadu.modules.capture.infrastructure.orm import ObservationRow
from sadu.modules.mapping import api as mapping
from sadu.modules.sites.infrastructure.orm import RegionPackRow, SiteRow
from sadu.shared.vocabulary import DamageType, Severity
from tests.integration.test_maps_api import (
    LONG_TEST_PHRASE,
    PHOTO,
    client,
    create_map,
    detector,
    login,
)

__all__ = ["client", "detector"]

ADMIN = "admin@example.org"
AUTHORITY = "authority@example.org"
NEW_PHRASE = "a brand new pass phrase"


@pytest.fixture
async def other_site_id(committed_unit_of_work, client) -> str:
    async with committed_unit_of_work() as session:
        await admin.create_user(session, ADMIN, LONG_TEST_PHRASE, admin.Role.ADMIN)
        await admin.create_user(session, AUTHORITY, LONG_TEST_PHRASE, admin.Role.AUTHORITY)
        pack = RegionPackRow(code="governance-test", name_ar="اختبار", name_en="Test", version="1")
        session.add(pack)
        await session.flush()
        site = SiteRow(
            pack_id=pack.id,
            slug="other-fort",
            name_ar="قلعة أخرى",
            name_en="Other fort",
            building_type="fort",
            location="SRID=4326;POINT(46.70 24.70)",
            boundary="SRID=4326;POLYGON((46.69 24.69, 46.71 24.69, 46.71 24.71, 46.69 24.71, 46.69 24.69))",
        )
        session.add(site)
        await session.flush()
        return str(site.id)


async def north_facade_id(client) -> str:
    facades = [f for site in (await client.get("/sites")).json() for f in site["facades"]]
    return next(f["id"] for f in facades if f["code"] == "north")


async def user_id(client, email: str) -> str:
    return next(u["id"] for u in (await client.get("/admin/users")).json() if u["email"] == email)


async def test_admin_creates_an_account_that_must_set_its_own_password(client, other_site_id):
    inspector = await login(client, "inspector@example.org")
    assert (await client.get("/admin/users")).status_code == 403
    assert (
        await client.post(
            "/admin/users",
            json={"email": "x@example.org", "role": "inspector", "password": "p"},
            headers=inspector,
        )
    ).status_code == 403

    headers = await login(client, ADMIN)
    new_user = {
        "email": "Surveyor@Example.org",
        "display_name": "مساح جديد",
        "role": "inspector",
        "password": LONG_TEST_PHRASE,
        "site_ids": [other_site_id],
    }
    created = await client.post("/admin/users", json=new_user, headers=headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["email"] == "surveyor@example.org" and body["display_name"] == "مساح جديد"
    assert body["must_change_password"] is True and body["is_active"] is True
    assert body["site_ids"] == [other_site_id]
    assert not any("password" in key and key != "must_change_password" for key in body)
    assert LONG_TEST_PHRASE not in created.text

    duplicate = await client.post("/admin/users", json=new_user, headers=headers)
    assert duplicate.status_code == 409
    short = await client.post(
        "/admin/users", json={**new_user, "email": "b@example.org", "password": "short"}, headers=headers
    )
    assert short.status_code == 422 and short.json()["code"] == "weak_password"
    unknown = {**new_user, "email": "c@example.org", "site_ids": ["00000000-0000-0000-0000-000000000000"]}
    assert (await client.post("/admin/users", json=unknown, headers=headers)).json()["code"] == "unknown_site"

    listed = {u["email"]: u for u in (await client.get("/admin/users")).json()}
    assert listed["surveyor@example.org"]["last_login_at"] is None
    assert listed[ADMIN]["last_login_at"] is not None

    surveyor = await login(client, "surveyor@example.org")
    me = (await client.get("/auth/me")).json()
    assert me["must_change_password"] is True and me["site_ids"] == [other_site_id]
    blocked = await client.get("/sites")
    assert blocked.status_code == 403 and blocked.json()["code"] == "password_change_required"

    wrong = await client.post(
        "/auth/password", json={"current_password": "not it", "new_password": NEW_PHRASE}, headers=surveyor
    )
    assert wrong.status_code == 401
    same = await client.post(
        "/auth/password",
        json={"current_password": LONG_TEST_PHRASE, "new_password": LONG_TEST_PHRASE},
        headers=surveyor,
    )
    assert same.status_code == 422
    changed = await client.post(
        "/auth/password",
        json={"current_password": LONG_TEST_PHRASE, "new_password": NEW_PHRASE},
        headers=surveyor,
    )
    assert changed.status_code == 204
    assert [s["slug"] for s in (await client.get("/sites")).json()] == ["other-fort"]


async def test_a_deactivated_account_cannot_sign_in_and_loses_its_sessions(client, other_site_id):
    await login(client, "inspector@example.org")
    inspector_session = client.cookies["sadu_session"]

    headers = await login(client, ADMIN)
    inspector_id = await user_id(client, "inspector@example.org")
    own = await client.post(
        f"/admin/users/{await user_id(client, ADMIN)}/active", json={"active": False}, headers=headers
    )
    assert own.status_code == 409 and own.json()["code"] == "own_account"

    disabled = await client.post(
        f"/admin/users/{inspector_id}/active", json={"active": False}, headers=headers
    )
    assert disabled.status_code == 200 and disabled.json()["is_active"] is False

    client.cookies.set("sadu_session", inspector_session)
    assert (await client.get("/auth/me")).status_code == 401
    refused = await client.post(
        "/auth/login", json={"email": "inspector@example.org", "password": LONG_TEST_PHRASE}
    )
    assert refused.status_code == 401 and refused.json()["code"] == "account_disabled"

    client.cookies.clear()
    headers = await login(client, ADMIN)
    enabled = await client.post(f"/admin/users/{inspector_id}/active", json={"active": True}, headers=headers)
    assert enabled.json()["is_active"] is True
    await login(client, "inspector@example.org")


async def test_role_change_and_password_reset_take_effect_and_are_audited(client, other_site_id):
    headers = await login(client, ADMIN)
    inspector_id = await user_id(client, "inspector@example.org")
    promoted = await client.post(
        f"/admin/users/{inspector_id}/role", json={"role": "expert"}, headers=headers
    )
    assert promoted.json()["role"] == "expert"
    reset = await client.post(
        f"/admin/users/{inspector_id}/password", json={"temporary_password": NEW_PHRASE}, headers=headers
    )
    assert reset.json()["must_change_password"] is True

    old = await client.post(
        "/auth/login", json={"email": "inspector@example.org", "password": LONG_TEST_PHRASE}
    )
    assert old.status_code == 401
    fresh = await client.post("/auth/login", json={"email": "inspector@example.org", "password": NEW_PHRASE})
    assert fresh.json()["role"] == "expert" and fresh.json()["must_change_password"] is True

    await login(client, ADMIN)
    trail = (await client.get("/admin/audit", params={"action": "user."})).json()
    actions = [e["action"] for e in trail["entries"]]
    assert actions == ["user.password_reset", "user.role"]
    assert trail["entries"][1]["details"] == {"from": "inspector", "to": "expert"}
    assert trail["entries"][1]["actor_email"] == ADMIN


async def test_scoped_users_get_404_for_sites_and_maps_outside_their_scope(client, detector, other_site_id):
    detector.cells = [("H1", DamageType.BASAL_EROSION, Severity.URGENT)]
    expert = await login(client, "expert@example.org")
    [demo] = [s for s in (await client.get("/sites")).json() if s["slug"] != "other-fort"]
    other_map = await create_map(
        client, expert, {"site_id": other_site_id, "wall_name": "سور", "width_m": 5, "height_m": 3}
    )
    assert other_map.status_code == 201, other_map.text
    other_map_id = other_map.json()["id"]

    headers = await login(client, ADMIN)
    inspector_id = await user_id(client, "inspector@example.org")
    scoped = await client.post(
        f"/admin/users/{inspector_id}/sites", json={"site_ids": [demo["id"]]}, headers=headers
    )
    assert scoped.json()["site_ids"] == [demo["id"]]
    authority_id = await user_id(client, AUTHORITY)
    await client.post(f"/admin/users/{authority_id}/sites", json={"site_ids": [demo["id"]]}, headers=headers)

    inspector = await login(client, "inspector@example.org")
    assert [s["id"] for s in (await client.get("/sites")).json()] == [demo["id"]]
    assert (await client.get(f"/sites/{demo['id']}/condition")).status_code == 200
    hidden = await client.get(f"/sites/{other_site_id}/condition")
    assert hidden.status_code == 404 and hidden.json()["code"] == "not_found"
    assert (await client.get(f"/maps/{other_map_id}")).status_code == 404
    assert (await client.get("/maps", params={"site_id": other_site_id})).status_code == 404
    assert other_map_id not in [m["id"] for m in (await client.get("/maps")).json()]
    refused = await create_map(
        client, inspector, {"site_id": other_site_id, "wall_name": "سور", "width_m": 5, "height_m": 3}
    )
    assert refused.status_code == 404
    assert (
        await create_map(client, inspector, {"facade_id": await north_facade_id(client)})
    ).status_code == 201

    await login(client, AUTHORITY)
    assert len((await client.get("/sites")).json()) == 2
    assert (await client.get(f"/maps/{other_map_id}")).status_code == 200


async def test_audit_trail_is_filterable_and_exportable_by_the_authority_only(
    client, detector, other_site_id
):
    inspector = await login(client, "inspector@example.org")
    await create_map(client, inspector, {"facade_id": await north_facade_id(client)})
    assert (await client.get("/admin/audit")).status_code == 403
    assert (await client.get("/admin/audit.csv")).status_code == 403

    await login(client, AUTHORITY)
    everything = (await client.get("/admin/audit")).json()
    assert everything["total"] == len(everything["entries"]) >= 3
    maps_only = (await client.get("/admin/audit", params={"action": "map."})).json()
    assert [e["action"] for e in maps_only["entries"]] == ["map.create"]
    by_actor = (await client.get("/admin/audit", params={"actor": "INSPECTOR@"})).json()
    assert {e["actor_email"] for e in by_actor["entries"]} == {"inspector@example.org"}
    by_target = (await client.get("/admin/audit", params={"target_type": "damage_map"})).json()
    assert {e["target_type"] for e in by_target["entries"]} == {"damage_map"}
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert (await client.get("/admin/audit", params={"from": future})).json()["total"] == 0
    paged = (await client.get("/admin/audit", params={"page_size": 1, "page": 2})).json()
    assert len(paged["entries"]) == 1 and paged["total"] == everything["total"]

    exported = await client.get("/admin/audit.csv", params={"action": "map."})
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert exported.content.startswith("﻿".encode())
    rows = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert rows[0][2] == "الإجراء" and [r[2] for r in rows[1:]] == ["map.create"]

    await login(client, ADMIN)
    assert (await client.get("/admin/audit")).status_code == 200


async def test_condition_and_elements_export_as_excel_friendly_csv_and_pdf(client, detector, other_site_id):
    detector.cells = [
        ("H1", DamageType.BASAL_EROSION, Severity.URGENT),
        ("B2", DamageType.CRACK, Severity.WATCH),
    ]
    inspector = await login(client, "inspector@example.org")
    created = await create_map(client, inspector, {"facade_id": await north_facade_id(client)})
    map_id = created.json()["id"]
    [demo] = [s for s in (await client.get("/sites")).json() if s["slug"] != "other-fort"]
    assert (await client.get(f"/sites/{demo['id']}/condition.csv")).status_code == 403
    assert (await client.get(f"/maps/{map_id}/elements.csv")).status_code == 403

    await login(client, AUTHORITY)
    condition = await client.get(f"/sites/{demo['id']}/condition.csv")
    assert condition.status_code == 200 and condition.content.startswith(b"\xef\xbb\xbf")
    assert "attachment" in condition.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(condition.content.decode("utf-8-sig"))))
    assert rows[0][:3] == ["الجدار", "الحالة", "تاريخ المسح"]
    assert "مسودة" in [r[1] for r in rows[1:]]

    elements = await client.get(f"/maps/{map_id}/elements.csv")
    element_rows = list(csv.reader(io.StringIO(elements.content.decode("utf-8-sig"))))
    assert element_rows[0][:4] == ["رقم العنصر", "نوع التلف", "الفئة", "الخطورة"]
    assert {r[1] for r in element_rows[1:]} == {"تآكل القاعدة", "التشققات"}
    assert "عاجل" in [r[3] for r in element_rows[1:]]

    pdf = await client.get(f"/sites/{demo['id']}/condition.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


async def test_urgent_maps_and_overdue_approvals_raise_one_notice_each(
    client, detector, committed_unit_of_work, other_site_id
):
    detector.cells = [("H1", DamageType.BASAL_EROSION, Severity.URGENT)]
    inspector = await login(client, "inspector@example.org")
    urgent = (await create_map(client, inspector, {"facade_id": await north_facade_id(client)})).json()
    detector.cells = [("B2", DamageType.CRACK, Severity.WATCH)]
    await create_map(client, inspector, {"facade_id": await north_facade_id(client)})

    await login(client, AUTHORITY)
    notices = (await client.get("/admin/audit", params={"action": "notice."})).json()["entries"]
    assert [(n["action"], n["target_id"], n["actor_id"]) for n in notices] == [
        ("notice.map_urgent", urgent["id"], None)
    ]

    later = datetime.now(UTC) + timedelta(days=8)
    async with committed_unit_of_work() as session:
        first = await mapping.announce_overdue_approvals(
            session, waiting_longer_than=timedelta(days=7), origin="https://athar.test", now=later
        )
    async with committed_unit_of_work() as session:
        again = await mapping.announce_overdue_approvals(
            session, waiting_longer_than=timedelta(days=7), origin="https://athar.test", now=later
        )
    assert len(first) == 2 and again == []
    assert first[0].kind == "notice.approval_overdue"
    assert first[0].link.startswith("https://athar.test/dashboard/maps/")


async def test_retention_purges_expired_photos_but_keeps_evidence(
    client, store, committed_unit_of_work, other_site_id
):
    async with committed_unit_of_work() as session:
        expired, _ = await capture.create_observation(
            session, store, raw_photo=PHOTO, meta=capture.CaptureMeta(datetime.now(UTC)), idempotency_key="a"
        )
        evidence, _ = await capture.create_observation(
            session, store, raw_photo=PHOTO, meta=capture.CaptureMeta(datetime.now(UTC)), idempotency_key="b"
        )
        await capture.keep_as_evidence(session, evidence.id)
        fresh, _ = await capture.create_observation(
            session, store, raw_photo=PHOTO, meta=capture.CaptureMeta(datetime.now(UTC)), idempotency_key="c"
        )
        await session.execute(
            update(ObservationRow)
            .where(ObservationRow.id == expired.id)
            .values(delete_after=datetime.now(UTC) - timedelta(days=1))
        )

    inspector = await login(client, "inspector@example.org")
    assert (await client.post("/admin/retention/run", headers=inspector)).status_code == 403
    headers = await login(client, ADMIN)
    run = await client.post("/admin/retention/run", headers=headers)
    assert run.status_code == 200, run.text
    assert run.json() == {"observations_deleted": 1, "objects_deleted": 1}
    assert expired.object_key not in store.objects
    assert evidence.object_key in store.objects and fresh.object_key in store.objects

    async with committed_unit_of_work() as session:
        remaining = set(await session.scalars(select(ObservationRow.id)))
    result = await agents.purge_expired_photos(
        committed_unit_of_work, store, now=datetime.now(UTC) + timedelta(days=31)
    )
    assert remaining == {evidence.id, fresh.id}
    assert result.observations == 1

    purges = (await client.get("/admin/audit", params={"action": "retention."})).json()["entries"]
    assert [(p["actor_email"], p["details"]["trigger"]) for p in purges] == [
        (None, "schedule"),
        (ADMIN, "admin"),
    ]


async def test_a_failed_detector_shows_a_flagged_detection_step(client, detector, other_site_id):
    detector.down = True
    inspector = await login(client, "inspector@example.org")
    body = (await create_map(client, inspector, {"facade_id": await north_facade_id(client)})).json()
    detect = body["workflow"][2]
    assert (detect["state"], detect["output_ar"]) == ("flagged", "تعذّر التحليل الآلي، ارسم العناصر يدويًا")
