import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from sadu.modules.watch.application.ports import WatchArea
from sadu.modules.watch.domain.change import Threat
from sadu.modules.watch.domain.geometry import pixel_centres, zones
from sadu.modules.watch.domain.scene import Band, Scene

REVISIT_DAYS = 5
CLOUDY_EVERY = 4
TEXTURE = 0.008

Surface = dict[Band, float]


def _surface(*reflectance: float) -> Surface:
    return dict(zip(Band, reflectance, strict=True))


DESERT = _surface(0.20, 0.25, 0.30, 0.35, 0.45, 0.40)
MUD_BRICK = _surface(0.22, 0.26, 0.31, 0.34, 0.40, 0.36)
PALMS = _surface(0.05, 0.08, 0.06, 0.35, 0.20, 0.10)
EVENT_SURFACES: dict[Threat, Surface] = {
    Threat.WATER: _surface(0.08, 0.10, 0.07, 0.04, 0.02, 0.01),
    Threat.CONSTRUCTION: _surface(0.28, 0.30, 0.32, 0.30, 0.52, 0.48),
    Threat.EARTHWORKS: _surface(0.14, 0.18, 0.22, 0.26, 0.32, 0.30),
    Threat.SAND: _surface(0.26, 0.34, 0.50, 0.44, 0.64, 0.60),
    Threat.VEGETATION_LOSS: DESERT,
}


@dataclass(frozen=True)
class SampleEvent:
    threat: Threat
    starts: date
    east_m: float
    north_m: float
    size_m: float


class SampleSceneSource:
    def __init__(self, events_path: Path | None) -> None:
        self._events = _load_events(events_path)

    @property
    def name(self) -> str:
        return "sample"

    @property
    def is_sample(self) -> bool:
        return True

    async def scenes(self, area: WatchArea, start: date, end: date, limit: int) -> list[Scene]:
        days = [start + timedelta(days=d) for d in range(0, (end - start).days + 1, REVISIT_DAYS)]
        if len(days) > limit:
            step = len(days) / limit
            days = [days[int(i * step)] for i in range(limit)]
        return [self._scene(area, day) for day in days]

    def _scene(self, area: WatchArea, day: date) -> Scene:
        seed = int(hashlib.sha256(f"{area.slug}:{day.isoformat()}".encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        size = area.window.size_px
        site = zones(area.boundary, area.center, area.window, buffer_m=0).inside
        x, y = pixel_centres(area.window)
        bands = {}
        for band in Band:
            layer = np.full((size, size), DESERT[band], np.float32)
            layer[site] = MUD_BRICK[band]
            bands[band] = layer
        for event in self._events.get(area.slug, []):
            patch = (np.abs(x - event.east_m) <= event.size_m / 2) & (
                np.abs(y - event.north_m) <= event.size_m / 2
            )
            surface = EVENT_SURFACES[event.threat] if day >= event.starts else None
            if event.threat is Threat.VEGETATION_LOSS and day < event.starts:
                surface = PALMS
            if surface is not None:
                for band in Band:
                    bands[band][patch] = surface[band]
        for band in Band:
            bands[band] += rng.normal(0, TEXTURE, (size, size)).astype(np.float32)
        clear = np.ones((size, size), bool)
        if seed % CLOUDY_EVERY == 0:
            row = int(rng.integers(0, size))
            clear[max(0, row - size // 4) : row + size // 4, :] = False
        return Scene(day, bands, clear)


def _load_events(path: Path | None) -> dict[str, list[SampleEvent]]:
    if path is None or not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        slug: [
            SampleEvent(
                Threat(e["threat"]),
                date.fromisoformat(e["starts"]),
                float(e["east_m"]),
                float(e["north_m"]),
                float(e["size_m"]),
            )
            for e in events
        ]
        for slug, events in raw["events"].items()
    }
