from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from sadu.modules.ingest.domain.devices import capture_due
from sadu.modules.ingest.domain.geo import (
    EARTH_RADIUS_M,
    FacadeFootprint,
    GeoPoint,
    distance_m,
    east_north_offset_m,
    nearest_facade,
)
from sadu.modules.ingest.domain.jobs import retry_delay

SITE = GeoPoint(24.7136, 46.6753)
METRE_IN_LAT_DEG = 1 / 111_195

NORTH, EAST, SOUTH, WEST = uuid4(), uuid4(), uuid4(), uuid4()
DEMO_FACADES = [
    FacadeFootprint.from_site_corners(NORTH, [[5, 0, -4], [-5, 0, -4], [-5, 6, -4], [5, 6, -4]], 0.0),
    FacadeFootprint.from_site_corners(EAST, [[5, 0, 4], [5, 0, -4], [5, 6, -4], [5, 6, 4]], 90.0),
    FacadeFootprint.from_site_corners(SOUTH, [[-5, 0, 4], [5, 0, 4], [5, 6, 4], [-5, 6, 4]], 180.0),
    FacadeFootprint.from_site_corners(WEST, [[-5, 0, -4], [-5, 0, 4], [-5, 6, 4], [-5, 6, -4]], 270.0),
]


def moved(point: GeoPoint, north_m: float = 0.0, east_m: float = 0.0) -> GeoPoint:
    lat = point.lat + north_m * METRE_IN_LAT_DEG
    lon = point.lon + east_m * METRE_IN_LAT_DEG / 0.9081
    return GeoPoint(lat, lon)


@pytest.mark.parametrize(
    ("north_m", "east_m", "expected"),
    [
        (15, 0, NORTH),
        (-20, 1, SOUTH),
        (0, 25, EAST),
        (2, -18, WEST),
        (12, 14, NORTH),
    ],
)
def test_photo_position_picks_the_facade_it_faces(north_m: float, east_m: float, expected: object) -> None:
    assert nearest_facade(SITE, moved(SITE, north_m, east_m), DEMO_FACADES) == expected


def test_photo_inside_the_footprint_falls_back_to_the_closest_wall() -> None:
    assert nearest_facade(SITE, moved(SITE, north_m=3.5), DEMO_FACADES) == NORTH


def test_no_facades_means_no_match() -> None:
    assert nearest_facade(SITE, moved(SITE, north_m=10), []) is None


def test_distance_and_offset_agree_for_short_hops() -> None:
    target = moved(SITE, north_m=30, east_m=40)
    east, north = east_north_offset_m(SITE, target)
    assert east == pytest.approx(40, abs=0.5)
    assert north == pytest.approx(30, abs=0.5)
    assert distance_m(SITE, target) == pytest.approx(50, abs=0.5)


def test_one_degree_of_latitude_is_about_111_km() -> None:
    assert distance_m(GeoPoint(0, 0), GeoPoint(1, 0)) == pytest.approx(EARTH_RADIUS_M * 0.017453, rel=1e-3)


@pytest.mark.parametrize(
    ("attempts", "expected"),
    [(1, timedelta(minutes=1)), (2, timedelta(minutes=2)), (3, None), (7, None)],
)
def test_failed_jobs_back_off_then_give_up(attempts: int, expected: timedelta | None) -> None:
    assert retry_delay(attempts) == expected


def test_camera_is_due_after_its_interval() -> None:
    now = datetime(2026, 11, 20, 12, tzinfo=UTC)
    day = timedelta(hours=24)
    assert capture_due(None, day, now)
    assert capture_due(now - day, day, now)
    assert not capture_due(now - timedelta(hours=23, minutes=59), day, now)
