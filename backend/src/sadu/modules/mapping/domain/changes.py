from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from sadu.modules.mapping.domain.damage_map import MapCell
from sadu.modules.mapping.domain.grid import CellRef


class ChangeKind(StrEnum):
    NEW = "new"
    WORSE = "worse"
    RETYPED = "retyped"
    IMPROVED = "improved"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class CellChange:
    ref: CellRef
    kind: ChangeKind
    before: MapCell | None
    after: MapCell | None


def compare_maps(before: Iterable[MapCell], after: Iterable[MapCell]) -> list[CellChange]:
    old = {cell.ref: cell for cell in before}
    new = {cell.ref: cell for cell in after}
    changes = []
    for ref in sorted(old.keys() | new.keys()):
        kind = _kind(old.get(ref), new.get(ref))
        if kind is not None:
            changes.append(CellChange(ref, kind, old.get(ref), new.get(ref)))
    return changes


def _kind(before: MapCell | None, after: MapCell | None) -> ChangeKind | None:
    if before is None and after is not None:
        return ChangeKind.NEW
    if before is not None and after is None:
        return ChangeKind.RESOLVED
    if before is None or after is None:
        return None
    if after.severity.rank > before.severity.rank:
        return ChangeKind.WORSE
    if after.damage_type is not before.damage_type:
        return ChangeKind.RETYPED
    if after.severity.rank < before.severity.rank:
        return ChangeKind.IMPROVED
    return None
