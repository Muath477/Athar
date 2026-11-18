from collections.abc import Iterable
from dataclasses import dataclass

from sadu.modules.mapping.domain.damage_map import MAP_DAMAGE_TYPES, CellSource, MapCell, keep_strongest
from sadu.modules.mapping.domain.grid import Box, CellRef, Grid
from sadu.shared.vocabulary import DamageType, ModelConfidence, Severity

MIN_CELL_COVERAGE = 0.15
HIGH_SCORE = 0.75
MEDIUM_SCORE = 0.5


@dataclass(frozen=True)
class Detection:
    damage_type: DamageType
    score: float
    box: Box
    severity: Severity | None = None


@dataclass(frozen=True)
class CellPrediction:
    ref: CellRef
    damage_type: DamageType
    score: float


def confidence_from_score(score: float) -> ModelConfidence:
    if score >= HIGH_SCORE:
        return ModelConfidence.HIGH
    if score >= MEDIUM_SCORE:
        return ModelConfidence.MEDIUM
    return ModelConfidence.LOW


def cells_from_detections(
    detections: Iterable[Detection], grid: Grid, *, min_score: float, min_coverage: float = MIN_CELL_COVERAGE
) -> tuple[MapCell, ...]:
    cells = []
    for detection in detections:
        if detection.score < min_score or detection.damage_type not in MAP_DAMAGE_TYPES:
            continue
        for ref, fraction in grid.coverage(detection.box).items():
            if fraction >= min_coverage:
                cells.append(
                    MapCell(
                        ref,
                        detection.damage_type,
                        detection.severity or Severity.WATCH,
                        confidence_from_score(detection.score),
                        CellSource.MODEL,
                    )
                )
    return keep_strongest(cells)


def cells_from_predictions(predictions: Iterable[CellPrediction], *, min_score: float) -> tuple[MapCell, ...]:
    cells = [
        MapCell(p.ref, p.damage_type, Severity.WATCH, confidence_from_score(p.score), CellSource.MODEL)
        for p in predictions
        if p.score >= min_score and p.damage_type in MAP_DAMAGE_TYPES
    ]
    return keep_strongest(cells)
