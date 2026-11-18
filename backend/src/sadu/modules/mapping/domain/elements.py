import itertools
import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from sadu.modules.mapping.domain.damage_map import CellSource, MapCell
from sadu.modules.mapping.domain.glossary import CLASS_VALUES, Geometry, entry_for
from sadu.modules.mapping.domain.grid import CellRef, Grid, WallSize
from sadu.shared.vocabulary import DamageType, ModelConfidence, Severity

Point = tuple[float, float]

LINE_BAND_M = 0.1
POINT_AREA_M2 = 0.04
MIN_POINTS = {Geometry.AREA: 3, Geometry.LINE: 2, Geometry.POINT: 1}
MAX_POINTS = 200


@dataclass(frozen=True)
class Element:
    id: str
    damage_type: DamageType
    points: tuple[Point, ...]
    severity: Severity
    confidence: ModelConfidence
    source: CellSource
    damage_class: str | None = None

    def __post_init__(self) -> None:
        entry = entry_for(self.damage_type)
        needed = MIN_POINTS[entry.geometry]
        count = len(self.points)
        if count < needed or count > MAX_POINTS or (entry.geometry is Geometry.POINT and count != 1):
            raise ValueError(f"{self.damage_type} needs a {entry.geometry} with valid points, got {count}")
        if not all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in self.points):
            raise ValueError("Element points must lie on the wall")
        if self.damage_class is not None:
            allowed = CLASS_VALUES[entry.class_kind] if entry.class_kind else ()
            if self.damage_class not in allowed:
                raise ValueError(f"{self.damage_class} is not a class of {self.damage_type}")

    @property
    def geometry(self) -> Geometry:
        return entry_for(self.damage_type).geometry

    @property
    def needs_review(self) -> bool:
        return self.source is CellSource.MODEL and self.confidence is ModelConfidence.LOW

    def centroid(self) -> Point:
        xs, ys = zip(*self.points, strict=True)
        return sum(xs) / len(xs), sum(ys) / len(ys)


@dataclass(frozen=True)
class Measurement:
    area_m2: float = 0.0
    length_m: float = 0.0
    count: int = 0

    @property
    def footprint_m2(self) -> float:
        return self.area_m2 + self.length_m * LINE_BAND_M + self.count * POINT_AREA_M2


def measure(element: Element, wall: WallSize) -> Measurement:
    metres = [(x * wall.width_m, y * wall.height_m) for x, y in element.points]
    if element.geometry is Geometry.AREA:
        return Measurement(area_m2=round(_polygon_area(metres), 3))
    if element.geometry is Geometry.LINE:
        return Measurement(length_m=round(_polyline_length(metres), 3))
    return Measurement(count=1)


def location_label(element: Element, grid: Grid) -> str:
    x, y = element.centroid()
    ref = CellRef(min(grid.rows - 1, int(y * grid.rows)), min(grid.cols - 1, int(x * grid.cols)))
    return ref.label


def elements_from_cells(cells: Iterable[MapCell], grid: Grid) -> tuple[Element, ...]:
    elements: list[Element] = []
    for cluster in _clusters(cells, lambda t: entry_for(t).geometry is Geometry.LINE):
        damage_type = cluster[0].damage_type
        severity = max((c.severity for c in cluster), key=lambda s: s.rank)
        confidence = min((c.confidence for c in cluster), key=_CONFIDENCE_ORDER.index)
        by_expert = all(c.source is CellSource.EXPERT for c in cluster)
        source = CellSource.EXPERT if by_expert else CellSource.MODEL
        refs = [c.ref for c in cluster]
        geometry = entry_for(damage_type).geometry
        shapes: list[tuple[Point, ...]]
        if geometry is Geometry.POINT:
            shapes = [(_centre(ref, grid),) for ref in refs]
        elif geometry is Geometry.LINE:
            shapes = [_cell_path(refs, grid)]
        else:
            shapes = [_outline(refs, grid)]
        for shape in shapes:
            elements.append(
                Element(f"E{len(elements) + 1}", damage_type, shape, severity, confidence, source)
            )
    return tuple(elements)


class EditAction(StrEnum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"


@dataclass(frozen=True)
class ElementEdit:
    action: EditAction
    element_id: str | None = None
    element: Element | None = None


@dataclass(frozen=True)
class EditResult:
    elements: tuple[Element, ...]
    log: tuple[dict[str, object], ...] = field(default=())


def apply_edits(
    elements: Sequence[Element], edits: Iterable[ElementEdit], used_ids: Iterable[str] = ()
) -> EditResult:
    current = {e.id: e for e in elements}
    log: list[dict[str, object]] = []
    known = [*current, *used_ids]
    next_number = max((int(i[1:]) for i in known if i[1:].isdigit()), default=0) + 1
    for edit in edits:
        if edit.action is EditAction.ADD:
            if edit.element is None:
                raise ValueError("An added element needs its shape")
            added = _relabel(edit.element, f"E{next_number}")
            next_number += 1
            current[added.id] = added
            log.append({"action": edit.action.value, "element_id": added.id, "after": element_json(added)})
            continue
        if edit.element_id not in current:
            raise ValueError(f"Element {edit.element_id} is not on this map")
        before = current[edit.element_id]
        if edit.action is EditAction.DELETE:
            del current[edit.element_id]
            log.append({"action": edit.action.value, "element_id": before.id, "before": element_json(before)})
            continue
        if edit.element is None:
            raise ValueError("An updated element needs its new shape")
        if edit.element.geometry is not before.geometry:
            raise ValueError("An update cannot change an element's geometry")
        after = _relabel(edit.element, before.id)
        current[before.id] = after
        log.append(
            {
                "action": edit.action.value,
                "element_id": before.id,
                "before": element_json(before),
                "after": element_json(after),
            }
        )
    ordered = sorted(current.values(), key=lambda e: int(e.id[1:]) if e.id[1:].isdigit() else 0)
    return EditResult(tuple(ordered), tuple(log))


def element_json(element: Element) -> dict[str, object]:
    return {
        "id": element.id,
        "damage_type": element.damage_type.value,
        "points": [[round(x, 5), round(y, 5)] for x, y in element.points],
        "severity": element.severity.value,
        "confidence": element.confidence.value,
        "source": element.source.value,
        "damage_class": element.damage_class,
    }


def element_from_json(item: dict[str, object]) -> Element:
    points = item["points"]
    if not isinstance(points, list):
        raise ValueError("Element points must be a list")
    damage_class = item.get("damage_class")
    return Element(
        id=str(item["id"]),
        damage_type=DamageType(str(item["damage_type"])),
        points=tuple((float(p[0]), float(p[1])) for p in points),
        severity=Severity(str(item["severity"])),
        confidence=ModelConfidence(str(item["confidence"])),
        source=CellSource(str(item["source"])),
        damage_class=str(damage_class) if damage_class is not None else None,
    )


_CONFIDENCE_ORDER = (ModelConfidence.LOW, ModelConfidence.MEDIUM, ModelConfidence.HIGH)
_FOUR = ((1, 0), (-1, 0), (0, 1), (0, -1))
_EIGHT = (*_FOUR, (1, 1), (1, -1), (-1, 1), (-1, -1))


def _relabel(element: Element, element_id: str) -> Element:
    return Element(
        element_id,
        element.damage_type,
        element.points,
        element.severity,
        element.confidence,
        element.source,
        element.damage_class,
    )


def _clusters(cells: Iterable[MapCell], diagonal: Callable[[DamageType], bool]) -> list[list[MapCell]]:
    by_ref = {cell.ref: cell for cell in cells}
    seen: set[CellRef] = set()
    clusters = []
    for ref in sorted(by_ref):
        if ref in seen:
            continue
        damage_type = by_ref[ref].damage_type
        steps = _EIGHT if diagonal(damage_type) else _FOUR
        stack, cluster = [ref], []
        seen.add(ref)
        while stack:
            current = stack.pop()
            cluster.append(by_ref[current])
            for d_row, d_col in steps:
                neighbour = CellRef(current.row + d_row, current.col + d_col)
                cell = by_ref.get(neighbour)
                if cell is not None and neighbour not in seen and cell.damage_type is damage_type:
                    seen.add(neighbour)
                    stack.append(neighbour)
        clusters.append(sorted(cluster, key=lambda c: c.ref))
    return clusters


def _centre(ref: CellRef, grid: Grid) -> Point:
    return (ref.col + 0.5) / grid.cols, (ref.row + 0.5) / grid.rows


def _cell_path(refs: list[CellRef], grid: Grid) -> tuple[Point, ...]:
    rows = {r.row for r in refs}
    cols = {r.col for r in refs}
    tall = len(rows) >= len(cols)
    if tall:
        path = [
            (
                sum(r.col + 0.5 for r in refs if r.row == row)
                / sum(1 for r in refs if r.row == row)
                / grid.cols,
                (row + 0.5) / grid.rows,
            )
            for row in sorted(rows)
        ]
    else:
        path = [
            (
                (col + 0.5) / grid.cols,
                sum(r.row + 0.5 for r in refs if r.col == col)
                / sum(1 for r in refs if r.col == col)
                / grid.rows,
            )
            for col in sorted(cols)
        ]
    if len(path) == 1:
        x, y = path[0]
        half = 0.4 / grid.rows if tall else 0.4 / grid.cols
        if tall:
            return (x, max(0.0, y - half)), (x, min(1.0, y + half))
        return (max(0.0, x - half), y), (min(1.0, x + half), y)
    return tuple(path)


def _outline(refs: list[CellRef], grid: Grid) -> tuple[Point, ...]:
    edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for ref in refs:
        x, y = ref.col, ref.row
        corners = [(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)]
        for a, b in zip(corners, corners[1:] + corners[:1], strict=True):
            if (b, a) in edges:
                edges.remove((b, a))
            else:
                edges.add((a, b))
    following = {a: b for a, b in edges}
    loops: list[list[tuple[int, int]]] = []
    unvisited = set(following)
    while unvisited:
        start = min(unvisited)
        loop, point = [], start
        while point in unvisited:
            unvisited.remove(point)
            loop.append(point)
            point = following[point]
        loops.append(loop)
    outer = max(loops, key=lambda loop: abs(_polygon_area([(float(a), float(b)) for a, b in loop])))
    corners = [p for i, p in enumerate(outer) if not _collinear(outer[i - 1], p, outer[(i + 1) % len(outer)])]
    return tuple((x / grid.cols, y / grid.rows) for x, y in corners)


def _collinear(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> bool:
    return (b[0] - a[0]) * (c[1] - b[1]) == (b[1] - a[1]) * (c[0] - b[0])


def _polygon_area(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1], strict=True):
        total += x0 * y1 - x1 * y0
    return abs(total) / 2


def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(math.dist(a, b) for a, b in itertools.pairwise(points))
