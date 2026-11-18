from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from sadu.modules.mapping.domain.damage_map import MapCell
from sadu.modules.mapping.domain.elements import Element
from sadu.modules.mapping.domain.grid import Grid
from sadu.shared.vocabulary import RetakeReason


@dataclass(frozen=True)
class DetectionInput:
    rectified_jpeg: bytes
    labeled_jpeg: bytes
    width_px: int
    height_px: int
    grid: Grid


@dataclass(frozen=True)
class DetectionOutput:
    cells: tuple[MapCell, ...]
    usable: bool = True
    retake_reason: RetakeReason | None = None
    summary_ar: str = ""
    elements: tuple[Element, ...] = ()
    model: str = ""
    prompt_version: str = ""


@dataclass(frozen=True)
class ModelChoice:
    name: str
    version: str


type ActiveModelLookup = Callable[[], Awaitable[ModelChoice | None]]


class DetectorUnavailable(Exception):
    pass


class DamageDetector(Protocol):
    @property
    def name(self) -> str: ...

    async def detect(self, request: DetectionInput) -> DetectionOutput: ...
