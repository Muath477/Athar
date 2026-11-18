from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit

import anyio
import httpx
import numpy as np
import numpy.typing as npt
import rasterio
from rasterio.enums import Resampling
from rasterio.errors import RasterioError
from rasterio.warp import transform as transform_points
from rasterio.windows import from_bounds

from sadu.modules.watch.application.ports import SceneSourceUnavailable, WatchArea
from sadu.modules.watch.domain.scene import Band, Scene

COLLECTION = "sentinel-2-c1-l2a"
SCENE_CLASSIFICATION = "scl"
CLEAR_CLASSES = (4, 5, 6)
MAX_CLOUD_COVER = 40
SEARCH_PAGE = 100
DEFAULT_SCALE = 0.0001
DEFAULT_OFFSET = -0.1
ALLOWED_ASSET_HOSTS = frozenset({"e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com"})
READ_DRIVER = "GTiff"
GDAL_OPTIONS: dict[str, str | int | bool] = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_TIMEOUT": 30,
    "GDAL_HTTP_MAX_RETRY": 3,
    "GDAL_HTTP_RETRY_DELAY": 1,
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "AWS_NO_SIGN_REQUEST": "YES",
    "VSI_CACHE": True,
}


@dataclass(frozen=True)
class Asset:
    href: str
    scale: float
    offset: float


@dataclass(frozen=True)
class StacItem:
    item_id: str
    acquired_on: date
    cloud_cover: float
    epsg: int
    assets: dict[str, Asset]


ItemReader = Callable[[StacItem, WatchArea], Scene]


class EarthSearchSceneSource:
    def __init__(
        self,
        search_url: str,
        *,
        timeout_s: float = 30.0,
        concurrent_reads: int = 4,
        reader: ItemReader | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._search_url = search_url
        self._timeout_s = timeout_s
        self._limiter = anyio.CapacityLimiter(concurrent_reads)
        self._reader = reader or read_item
        self._transport = transport

    @property
    def name(self) -> str:
        return "earth_search"

    @property
    def is_sample(self) -> bool:
        return False

    async def scenes(self, area: WatchArea, start: date, end: date, limit: int) -> list[Scene]:
        items = pick_items(await self._search(area, start, end), limit)
        scenes: list[Scene] = []
        failures = 0

        async def read(item: StacItem) -> None:
            nonlocal failures
            try:
                scenes.append(await anyio.to_thread.run_sync(self._reader, item, area, limiter=self._limiter))
            except (RasterioError, ValueError):
                failures += 1

        async with anyio.create_task_group() as group:
            for item in items:
                group.start_soon(read, item)
        if items and not scenes:
            raise SceneSourceUnavailable(f"Could not read any of {failures} Sentinel-2 scenes")
        return sorted(scenes, key=lambda scene: scene.acquired_on)

    async def _search(self, area: WatchArea, start: date, end: date) -> list[StacItem]:
        body = search_body(area, start, end)
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s, transport=self._transport) as client:
                response = await client.post(self._search_url, json=body)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise SceneSourceUnavailable(f"Earth Search did not answer: {error}") from error
        features = payload.get("features") if isinstance(payload, dict) else None
        if not isinstance(features, list):
            raise SceneSourceUnavailable("Earth Search returned no feature list")
        return [item for feature in features if (item := parse_item(feature)) is not None]


def search_body(area: WatchArea, start: date, end: date) -> dict[str, Any]:
    return {
        "collections": [COLLECTION],
        "intersects": {"type": "Point", "coordinates": [area.center.lon, area.center.lat]},
        "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
        "query": {"eo:cloud_cover": {"lt": MAX_CLOUD_COVER}},
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        "limit": SEARCH_PAGE,
    }


def parse_item(feature: object) -> StacItem | None:
    if not isinstance(feature, Mapping):
        return None
    properties = feature.get("properties")
    raw_assets = feature.get("assets")
    if not isinstance(properties, Mapping) or not isinstance(raw_assets, Mapping):
        return None
    acquired_on = _acquired_on(properties.get("datetime"))
    epsg = _epsg(properties)
    cloud_cover = properties.get("eo:cloud_cover")
    if acquired_on is None or epsg is None or not isinstance(cloud_cover, int | float):
        return None
    assets: dict[str, Asset] = {}
    for key in [*(band.value for band in Band), SCENE_CLASSIFICATION]:
        asset = _asset(raw_assets.get(key))
        if asset is None:
            return None
        assets[key] = asset
    return StacItem(
        item_id=str(feature.get("id", "")),
        acquired_on=acquired_on,
        cloud_cover=float(cloud_cover),
        epsg=epsg,
        assets=assets,
    )


def pick_items(items: list[StacItem], limit: int) -> list[StacItem]:
    clearest_per_day: dict[date, StacItem] = {}
    for item in sorted(items, key=lambda item: item.cloud_cover):
        clearest_per_day.setdefault(item.acquired_on, item)
    clearest = sorted(clearest_per_day.values(), key=lambda item: item.cloud_cover)[:limit]
    return sorted(clearest, key=lambda item: item.acquired_on)


def read_item(item: StacItem, area: WatchArea) -> Scene:
    with rasterio.Env(**GDAL_OPTIONS):
        xs, ys = transform_points("EPSG:4326", f"EPSG:{item.epsg}", [area.center.lon], [area.center.lat])
        half = area.window.half_extent_m
        bounds = (xs[0] - half, ys[0] - half, xs[0] + half, ys[0] + half)
        shape = (area.window.size_px, area.window.size_px)
        counts = {
            band: _read(item.assets[band.value].href, bounds, shape, Resampling.bilinear) for band in Band
        }
        classes = _read(item.assets[SCENE_CLASSIFICATION].href, bounds, shape, Resampling.nearest)
    observed = np.all(np.stack([count > 0 for count in counts.values()]), axis=0)
    clear = np.asarray(observed & np.isin(classes, CLEAR_CLASSES))
    bands = {
        band: np.asarray(
            count.astype(np.float32) * item.assets[band.value].scale + item.assets[band.value].offset,
            dtype=np.float32,
        )
        for band, count in counts.items()
    }
    return Scene(acquired_on=item.acquired_on, bands=bands, clear=clear)


def _read(
    href: str,
    bounds: tuple[float, float, float, float],
    shape: tuple[int, int],
    resampling: Resampling,
) -> npt.NDArray[np.uint16]:
    with rasterio.open(href, driver=READ_DRIVER) as dataset:
        window = from_bounds(*bounds, transform=dataset.transform)
        values = dataset.read(
            1,
            window=window,
            out_shape=shape,
            resampling=resampling,
            boundless=True,
            fill_value=0,
        )
    return np.asarray(values, dtype=np.uint16)


def _acquired_on(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _epsg(properties: Mapping[str, object]) -> int | None:
    code = properties.get("proj:code")
    if isinstance(code, str) and code.upper().startswith("EPSG:") and code[5:].isdigit():
        return int(code[5:])
    epsg = properties.get("proj:epsg")
    return epsg if isinstance(epsg, int) else None


def _asset(raw: object) -> Asset | None:
    if not isinstance(raw, Mapping):
        return None
    href = raw.get("href")
    if not isinstance(href, str) or not _allowed(href):
        return None
    scale, offset = DEFAULT_SCALE, DEFAULT_OFFSET
    bands = raw.get("raster:bands")
    if isinstance(bands, list) and bands and isinstance(bands[0], Mapping):
        scale = _number(bands[0].get("scale"), scale)
        offset = _number(bands[0].get("offset"), offset)
    return Asset(href=href, scale=scale, offset=offset)


def _allowed(href: str) -> bool:
    parts = urlsplit(href)
    return parts.scheme == "https" and parts.hostname in ALLOWED_ASSET_HOSTS and parts.path.endswith(".tif")


def _number(value: object, default: float) -> float:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else default
