from dataclasses import dataclass
from enum import StrEnum


class MapSource(StrEnum):
    INSPECTOR = "inspector"
    CAMERA = "camera"
    DRONE = "drone"
    UPLOAD = "upload"


@dataclass(frozen=True)
class Provenance:
    source: MapSource
    label: str | None = None
