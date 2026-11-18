import itertools
import json
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform as transform_points

from sadu.modules.watch.application.ports import SceneSourceUnavailable, WatchArea
from sadu.modules.watch.application.screening import BUFFER_M, screen
from sadu.modules.watch.domain.change import ChangeRules, ScreeningStatus, Threat, Zone
from sadu.modules.watch.domain.geometry import LatLon, window_for
from sadu.modules.watch.domain.risk import RiskLevel
from sadu.modules.watch.domain.scene import Band, Scene
from sadu.modules.watch.infrastructure.earth_search import (
    COLLECTION,
    Asset,
    EarthSearchSceneSource,
    StacItem,
    parse_item,
    read_item,
    search_body,
    time_bins,
)
from sadu.modules.watch.infrastructure.sample_source import SampleSceneSource

pytestmark = pytest.mark.anyio

CENTRE = LatLon(24.7341, 46.5725)
HOST = "https://e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com/sentinel-2-c1-l2a/38/R/PN"
ASSET_KEYS = [*(band.value for band in Band), "scl"]


def square(half_m: float) -> list[LatLon]:
    d_lat = half_m / 111_195
    d_lon = half_m / (111_195 * np.cos(np.radians(CENTRE.lat)))
    return [
        LatLon(CENTRE.lat + d_lat, CENTRE.lon - d_lon),
        LatLon(CENTRE.lat + d_lat, CENTRE.lon + d_lon),
        LatLon(CENTRE.lat - d_lat, CENTRE.lon + d_lon),
        LatLon(CENTRE.lat - d_lat, CENTRE.lon - d_lon),
    ]


AREA = WatchArea(uuid4(), "turaif", CENTRE, square(150), window_for(square(150), CENTRE, BUFFER_M))


def feature(day: str, cloud: float, host: str = HOST) -> dict:
    return {
        "id": f"S2B_38RPN_{day}",
        "properties": {"datetime": f"{day}T07:43:21.024000Z", "eo:cloud_cover": cloud, "proj:epsg": 32638},
        "assets": {
            key: {
                "href": f"{host}/{day}/{key.upper()}.tif",
                "raster:bands": [{"nodata": 0, "scale": 0.0001, "offset": -0.1}],
            }
            for key in ASSET_KEYS
        },
    }


def test_search_asks_for_low_cloud_collection_one_scenes_over_the_site():
    body = search_body(AREA, date(2026, 10, 1), date(2026, 10, 31))
    assert body["collections"] == [COLLECTION] == ["sentinel-2-c1-l2a"]
    assert body["intersects"]["coordinates"] == [CENTRE.lon, CENTRE.lat]
    assert body["datetime"] == "2026-10-01T00:00:00Z/2026-10-31T23:59:59Z"
    assert body["query"]["eo:cloud_cover"]["lt"] <= 40


def test_items_carry_their_reflectance_scale_and_offset():
    item = parse_item(feature("2026-10-05", 3.5))
    assert item is not None
    assert item.acquired_on == date(2026, 10, 5) and item.epsg == 32638
    assert item.assets["red"] == Asset(f"{HOST}/2026-10-05/RED.tif", 0.0001, -0.1)


@pytest.mark.parametrize(
    "host",
    [
        "https://attacker.example.org/cogs",
        "http://e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com/x",
        "file:///etc",
    ],
)
def test_assets_outside_the_sentinel_bucket_are_refused(host):
    assert parse_item(feature("2026-10-05", 3.5, host=host)) is None


def test_items_missing_a_band_are_skipped():
    broken = feature("2026-10-05", 3.5)
    del broken["assets"]["swir22"]
    assert parse_item(broken) is None


def test_time_bins_split_the_period_evenly_without_overlap():
    bins = time_bins(date(2025, 10, 18), date(2026, 10, 17), 16)
    assert len(bins) == 16
    assert bins[0][0] == date(2025, 10, 18) and bins[-1][1] == date(2026, 10, 17)
    assert all(later[0] == earlier[1] + timedelta(days=1) for earlier, later in itertools.pairwise(bins))
    assert time_bins(date(2026, 10, 1), date(2026, 10, 3), 6) == [
        (date(2026, 10, 1), date(2026, 10, 1)),
        (date(2026, 10, 2), date(2026, 10, 2)),
        (date(2026, 10, 3), date(2026, 10, 3)),
    ]


async def test_each_time_bin_contributes_its_clearest_scene():
    source = EarthSearchSceneSource(
        "https://catalog.test/search",
        reader=fake_scene,
        transport=catalog(
            [
                feature("2026-01-05", 30),
                feature("2026-01-20", 2),
                feature("2026-07-03", 0.1),
                feature("2026-07-04", 0.2),
            ]
        ),
    )
    scenes = await source.scenes(AREA, date(2026, 1, 1), date(2026, 12, 31), limit=2)
    assert [s.acquired_on for s in scenes] == [date(2026, 1, 20), date(2026, 7, 3)]


def fake_scene(item: StacItem, area: WatchArea) -> Scene:
    size = area.window.size_px
    bands = {band: np.full((size, size), 0.3, np.float32) for band in Band}
    return Scene(item.acquired_on, bands, np.ones((size, size), bool))


def catalog(features: list[dict], status: int = 200) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["collections"] == [COLLECTION]
        start, end = (part[:10] for part in body["datetime"].split("/"))
        inside = [f for f in features if start <= f["properties"]["datetime"][:10] <= end]
        return httpx.Response(status, json={"type": "FeatureCollection", "features": inside})

    return httpx.MockTransport(handle)


async def test_earth_search_returns_scenes_in_date_order():
    source = EarthSearchSceneSource(
        "https://catalog.test/search",
        reader=fake_scene,
        transport=catalog([feature("2026-10-11", 1), feature("2026-10-01", 4)]),
    )
    scenes = await source.scenes(AREA, date(2026, 10, 1), date(2026, 10, 31), limit=6)
    assert [s.acquired_on.day for s in scenes] == [1, 11]
    assert source.name == "earth_search" and not source.is_sample


async def test_a_catalog_outage_is_reported_as_unavailable():
    source = EarthSearchSceneSource("https://catalog.test/search", transport=catalog([], status=503))
    with pytest.raises(SceneSourceUnavailable):
        await source.scenes(AREA, date(2026, 10, 1), date(2026, 10, 31), limit=6)


async def test_scenes_that_cannot_be_read_make_the_source_unavailable():
    def unreadable(item: StacItem, area: WatchArea) -> Scene:
        raise rasterio.errors.RasterioIOError("HTTP 403")

    source = EarthSearchSceneSource(
        "https://catalog.test/search", reader=unreadable, transport=catalog([feature("2026-10-11", 1)])
    )
    with pytest.raises(SceneSourceUnavailable):
        await source.scenes(AREA, date(2026, 10, 1), date(2026, 10, 31), limit=6)


def write_tile(path: Path, values: np.ndarray, pixel_m: float, origin: tuple[float, float]) -> str:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=values.shape[1],
        height=values.shape[0],
        count=1,
        dtype=values.dtype,
        crs="EPSG:32638",
        transform=from_origin(origin[0], origin[1], pixel_m, pixel_m),
        nodata=0,
    ) as dataset:
        dataset.write(values, 1)
    return str(path)


def test_reading_a_tile_cuts_the_site_window_converts_to_reflectance_and_masks_clouds(tmp_path):
    xs, ys = transform_points("EPSG:4326", "EPSG:32638", [CENTRE.lon], [CENTRE.lat])
    origin = (round(xs[0]) - 2000.0, round(ys[0]) + 2000.0)
    fine = np.full((400, 400), 3000, np.uint16)
    coarse = np.full((200, 200), 4000, np.uint16)
    classes = np.full((200, 200), 5, np.uint8)
    classes[:100, :] = 9
    assets = {
        band.value: Asset(
            write_tile(
                tmp_path / f"{band.value}.tif",
                fine if band in {Band.BLUE, Band.GREEN, Band.RED, Band.NIR} else coarse,
                10.0 if band in {Band.BLUE, Band.GREEN, Band.RED, Band.NIR} else 20.0,
                origin,
            ),
            0.0001,
            -0.1,
        )
        for band in Band
    }
    assets["scl"] = Asset(write_tile(tmp_path / "scl.tif", classes, 20.0, origin), 1.0, 0.0)
    item = StacItem("local", date(2026, 10, 5), 1.0, 32638, assets)

    scene = read_item(item, AREA)

    size = AREA.window.size_px
    assert scene.shape == (size, size)
    assert scene.bands[Band.RED][size // 2, size // 2] == pytest.approx(0.2)
    assert scene.bands[Band.SWIR16][size // 2, size // 2] == pytest.approx(0.3)
    assert not scene.clear[0].any() and scene.clear[-1].all()


def events_file(tmp_path: Path, threat: Threat, east_m: float) -> Path:
    path = tmp_path / "sample-events.json"
    event = {"threat": threat.value, "starts": "2026-10-25", "east_m": east_m, "north_m": 0, "size_m": 60}
    path.write_text(json.dumps({"events": {"turaif": [event]}}), encoding="utf-8")
    return path


async def test_a_quiet_sample_site_screens_as_stable():
    screening = await screen(SampleSceneSource(None), AREA, date(2026, 11, 18), ChangeRules())
    assert screening.report.status is ScreeningStatus.OK
    assert screening.risk.level is RiskLevel.STABLE


@pytest.mark.parametrize(
    ("threat", "east_m", "zone"),
    [
        (Threat.CONSTRUCTION, 200.0, Zone.RING),
        (Threat.WATER, 0.0, Zone.INSIDE),
        (Threat.EARTHWORKS, 0.0, Zone.INSIDE),
        (Threat.SAND, 200.0, Zone.RING),
    ],
)
async def test_sample_events_are_found_by_the_detector(tmp_path, threat, east_m, zone):
    source = SampleSceneSource(events_file(tmp_path, threat, east_m))
    screening = await screen(source, AREA, date(2026, 11, 18), ChangeRules())
    strongest = screening.report.strongest()
    assert strongest is not None
    assert (strongest.threat, strongest.zone) == (threat, zone)
    assert screening.risk.level is not RiskLevel.STABLE


RIYADH_PACK = Path(__file__).resolve().parents[3] / "region-packs" / "riyadh"


def pack_area(site: dict) -> WatchArea:
    centre = LatLon(site["location"][1], site["location"][0])
    boundary = [LatLon(lat, lon) for lon, lat in site["boundary"]]
    return WatchArea(uuid4(), site["slug"], centre, boundary, window_for(boundary, centre, BUFFER_M))


def test_riyadh_pack_marks_both_world_heritage_properties():
    sites = json.loads((RIYADH_PACK / "pack.json").read_text(encoding="utf-8"))["sites"]
    assert len(sites) == 11
    assert {s["slug"] for s in sites if s["building_type"] == "world_heritage"} == {"at-turaif", "al-faw"}
    for site in sites:
        lon, lat = site["location"]
        assert 19 < lat < 27.5 and 42 < lon < 48.5


async def test_every_riyadh_sample_event_is_found_where_it_was_placed():
    sites = {
        s["slug"]: s for s in json.loads((RIYADH_PACK / "pack.json").read_text(encoding="utf-8"))["sites"]
    }
    events_path = RIYADH_PACK / "sample-events.json"
    events = json.loads(events_path.read_text(encoding="utf-8"))["events"]
    source = SampleSceneSource(events_path)
    for slug, [event] in events.items():
        screening = await screen(source, pack_area(sites[slug]), date(2026, 11, 18), ChangeRules())
        strongest = screening.report.strongest()
        assert strongest is not None, slug
        assert strongest.threat == Threat(event["threat"]), slug
