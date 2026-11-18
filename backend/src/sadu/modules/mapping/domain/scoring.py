from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sadu.modules.mapping.domain.damage_map import MAP_DAMAGE_TYPES
from sadu.modules.mapping.domain.grid import CellRef
from sadu.shared.vocabulary import DamageType

type CellLabels = Mapping[CellRef, DamageType]


@dataclass(frozen=True)
class TypeScore:
    damage_type: DamageType
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float | None:
        predicted = self.true_positives + self.false_positives
        return self.true_positives / predicted if predicted else None

    @property
    def recall(self) -> float | None:
        expected = self.true_positives + self.false_negatives
        return self.true_positives / expected if expected else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None or p + r == 0:
            return None
        return 2 * p * r / (p + r)


@dataclass(frozen=True)
class MapScore:
    maps: int
    cells: int
    damaged_vs_sound_accuracy: float | None
    by_type: tuple[TypeScore, ...]


@dataclass(frozen=True)
class ScoredPair:
    total_cells: int
    predicted: CellLabels
    expected: CellLabels


def score_maps(pairs: Iterable[ScoredPair]) -> MapScore:
    counts = {t: [0, 0, 0] for t in MAP_DAMAGE_TYPES}
    maps = cells = agree_on_damage = 0
    for pair in pairs:
        maps += 1
        cells += pair.total_cells
        agree_on_damage += pair.total_cells - len(pair.predicted.keys() ^ pair.expected.keys())
        for ref in pair.predicted.keys() | pair.expected.keys():
            predicted, expected = pair.predicted.get(ref), pair.expected.get(ref)
            if predicted is not None and predicted is expected:
                counts[predicted][0] += 1
                continue
            if predicted is not None and predicted in counts:
                counts[predicted][1] += 1
            if expected is not None and expected in counts:
                counts[expected][2] += 1
    return MapScore(
        maps=maps,
        cells=cells,
        damaged_vs_sound_accuracy=agree_on_damage / cells if cells else None,
        by_type=tuple(TypeScore(t, *counts[t]) for t in MAP_DAMAGE_TYPES),
    )
