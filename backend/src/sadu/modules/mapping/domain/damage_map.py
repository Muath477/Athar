from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import StrEnum

from sadu.modules.mapping.domain.grid import CellRef, Grid, WallSize
from sadu.shared.vocabulary import DamageType, ModelConfidence, Severity

MAP_DAMAGE_TYPES = (
    DamageType.PLASTER_LOSS,
    DamageType.CRACK,
    DamageType.BASAL_EROSION,
    DamageType.RAIN_GULLY,
    DamageType.SALT_EFFLORESCENCE,
    DamageType.CAVITY,
    DamageType.WALL_HEAD,
    DamageType.CEMENT_REPAIR,
    DamageType.MOISTURE,
    DamageType.SURFACE_EROSION,
    DamageType.PARTIAL_COLLAPSE,
    DamageType.GRAFFITI,
)


class CellSource(StrEnum):
    MODEL = "model"
    EXPERT = "expert"


class MapStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"


@dataclass(frozen=True)
class MapCell:
    ref: CellRef
    damage_type: DamageType
    severity: Severity
    confidence: ModelConfidence
    source: CellSource

    def __post_init__(self) -> None:
        if self.damage_type not in MAP_DAMAGE_TYPES:
            raise ValueError(f"{self.damage_type} is not a wall map damage type")


@dataclass(frozen=True)
class CellCorrection:
    ref: CellRef
    damage_type: DamageType
    severity: Severity

    @property
    def clears_cell(self) -> bool:
        return self.damage_type is DamageType.NONE


@dataclass(frozen=True)
class AreaTally:
    damage_type: DamageType
    severity: Severity
    cells: int
    area_m2: float


def apply_corrections(
    cells: Iterable[MapCell], corrections: Iterable[CellCorrection], grid: Grid
) -> tuple[MapCell, ...]:
    by_ref = {cell.ref: cell for cell in cells}
    for correction in corrections:
        if not grid.contains(correction.ref):
            raise ValueError(f"Cell {correction.ref.label} is outside the map grid")
        if correction.clears_cell:
            by_ref.pop(correction.ref, None)
            continue
        by_ref[correction.ref] = MapCell(
            correction.ref,
            correction.damage_type,
            correction.severity,
            ModelConfidence.HIGH,
            CellSource.EXPERT,
        )
    return tuple(sorted(by_ref.values(), key=lambda c: c.ref))


def keep_strongest(cells: Iterable[MapCell]) -> tuple[MapCell, ...]:
    best: dict[CellRef, MapCell] = {}
    for cell in cells:
        current = best.get(cell.ref)
        if current is None or _strength(cell) > _strength(current):
            best[cell.ref] = cell
    return tuple(sorted(best.values(), key=lambda c: c.ref))


def tally_areas(cells: Iterable[MapCell], grid: Grid, wall: WallSize) -> list[AreaTally]:
    counts: dict[tuple[DamageType, Severity], int] = defaultdict(int)
    for cell in cells:
        counts[(cell.damage_type, cell.severity)] += 1
    cell_area = grid.cell_area_m2(wall)
    return [
        AreaTally(damage_type, severity, count, count * cell_area)
        for (damage_type, severity), count in sorted(
            counts.items(), key=lambda kv: (-kv[0][1].rank, kv[0][0])
        )
    ]


def with_source(cells: Iterable[MapCell], source: CellSource) -> tuple[MapCell, ...]:
    return tuple(replace(cell, source=source) for cell in cells)


_CONFIDENCE_ORDER = (ModelConfidence.LOW, ModelConfidence.MEDIUM, ModelConfidence.HIGH)


def _strength(cell: MapCell) -> tuple[int, int]:
    return (cell.severity.rank, _CONFIDENCE_ORDER.index(cell.confidence))
