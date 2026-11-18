from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from sadu.modules.watch.domain.geometry import LatLon
from sadu.modules.watch.domain.scene import Scene, Window


@dataclass(frozen=True)
class WatchArea:
    site_id: UUID
    slug: str
    center: LatLon
    boundary: list[LatLon]
    window: Window


class SceneSourceUnavailable(Exception):
    pass


class SceneSource(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def is_sample(self) -> bool: ...

    async def scenes(self, area: WatchArea, start: date, end: date, limit: int) -> list[Scene]: ...
