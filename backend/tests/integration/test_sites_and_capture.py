from datetime import UTC, datetime

import pytest

from sadu.modules.capture import api as capture
from sadu.modules.sites import api as sites
from sadu.shared.errors import Conflict
from tests.integration.conftest import PACK_DIR


async def test_pack_import_creates_site_facades_and_baselines(session, store, demo):
    assert set(demo.facades) == {"north", "east", "south", "west"}
    baseline = await sites.primary_baseline(session, demo.facades["north"].id)
    assert baseline.object_key in store.objects
    assert baseline.to_uv(0, 0) == pytest.approx((0.0, 1.0), abs=1e-6)
    assert baseline.to_uv(baseline.width, baseline.height) == pytest.approx((1.0, 0.0), abs=1e-6)


async def test_reimporting_the_pack_replaces_the_site(session, store, demo):
    await sites.import_region_pack(session, store, PACK_DIR)
    assert [s.slug for s in await sites.list_sites(session)].count(demo.site.slug) == 1


async def test_sites_are_found_by_distance(session, demo):
    near = await sites.find_sites_near(session, lat=24.7136, lon=46.6753, radius_m=50)
    far = await sites.find_sites_near(session, lat=24.80, lon=46.70, radius_m=50)
    assert demo.site.id in {s.id for s in near}
    assert demo.site.id not in {s.id for s in far}


def photo_bytes(name: str) -> bytes:
    return (PACK_DIR / "test-photos" / name).read_bytes()


async def test_observation_replay_returns_the_same_row(session, store, demo):
    meta = capture.CaptureMeta(captured_at=datetime(2026, 11, 16, tzinfo=UTC), lat=24.7136, lon=46.6753)
    first, created = await capture.create_observation(
        session, store, raw_photo=photo_bytes("north-crack.jpg"), meta=meta, idempotency_key="k-1"
    )
    again, created_again = await capture.create_observation(
        session, store, raw_photo=photo_bytes("north-crack.jpg"), meta=meta, idempotency_key="k-1"
    )
    assert created and not created_again
    assert again.id == first.id
    assert first.lat == pytest.approx(24.7136) and first.lon == pytest.approx(46.6753)


async def test_reusing_a_key_for_another_photo_is_rejected(session, store, demo):
    meta = capture.CaptureMeta(captured_at=datetime(2026, 11, 16, tzinfo=UTC))
    await capture.create_observation(
        session, store, raw_photo=photo_bytes("north-crack.jpg"), meta=meta, idempotency_key="k-2"
    )
    with pytest.raises(Conflict):
        await capture.create_observation(
            session, store, raw_photo=photo_bytes("north-shadow.jpg"), meta=meta, idempotency_key="k-2"
        )


async def test_location_is_dropped_once_the_facade_is_known(session, store, demo):
    meta = capture.CaptureMeta(captured_at=datetime(2026, 11, 16, tzinfo=UTC), lat=24.7136, lon=46.6753)
    observation, _ = await capture.create_observation(
        session, store, raw_photo=photo_bytes("north-crack.jpg"), meta=meta, idempotency_key="k-3"
    )
    await capture.attach_location_result(
        session, observation.id, site_id=demo.site.id, facade_id=demo.facades["north"].id
    )
    stored = await capture.get_observation(session, observation.id)
    assert not stored.has_location and stored.lat is None and stored.heading_deg is None
    assert stored.facade_id == demo.facades["north"].id
