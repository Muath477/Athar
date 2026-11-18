import itertools
import math
from collections.abc import Iterable

from sadu.modules.mapping.domain.damage_map import CellSource, MapCell, keep_strongest
from sadu.modules.mapping.domain.detections import MIN_CELL_COVERAGE
from sadu.modules.mapping.domain.elements import Element, Point
from sadu.modules.mapping.domain.glossary import Geometry
from sadu.modules.mapping.domain.grid import CellRef, Grid

SAMPLES_PER_CELL_SIDE = 6
LINE_STEPS_PER_CELL = 8


def cells_from_elements(
    elements: Iterable[Element], grid: Grid, source: CellSource = CellSource.MODEL
) -> tuple[MapCell, ...]:
    cells = [
        MapCell(ref, element.damage_type, element.severity, element.confidence, source)
        for element in elements
        for ref in covered_cells(element, grid)
    ]
    return keep_strongest(cells)


def covered_cells(element: Element, grid: Grid) -> set[CellRef]:
    if element.geometry is Geometry.POINT:
        return {_cell_at(element.points[0], grid)}
    if element.geometry is Geometry.LINE:
        return _cells_on_polyline(element.points, grid)
    return _cells_in_polygon(element.points, grid)


def _cell_at(point: Point, grid: Grid) -> CellRef:
    x, y = point
    return CellRef(min(grid.rows - 1, int(y * grid.rows)), min(grid.cols - 1, int(x * grid.cols)))


def _cells_on_polyline(points: tuple[Point, ...], grid: Grid) -> set[CellRef]:
    cells: set[CellRef] = set()
    for (x0, y0), (x1, y1) in itertools.pairwise(points):
        span = max(abs(x1 - x0) * grid.cols, abs(y1 - y0) * grid.rows)
        steps = max(1, math.ceil(span * LINE_STEPS_PER_CELL))
        for step in range(steps + 1):
            t = step / steps
            cells.add(_cell_at((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), grid))
    return cells


def _cells_in_polygon(points: tuple[Point, ...], grid: Grid) -> set[CellRef]:
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    first = _cell_at((min(xs), min(ys)), grid)
    last = _cell_at((max(xs), max(ys)), grid)
    covered = set()
    for row in range(first.row, last.row + 1):
        for col in range(first.col, last.col + 1):
            if _polygon_share(points, row, col, grid) >= MIN_CELL_COVERAGE:
                covered.add(CellRef(row, col))
    return covered


def _polygon_share(points: tuple[Point, ...], row: int, col: int, grid: Grid) -> float:
    side = SAMPLES_PER_CELL_SIDE
    inside = 0
    for i in range(side):
        for j in range(side):
            x = (col + (j + 0.5) / side) / grid.cols
            y = (row + (i + 0.5) / side) / grid.rows
            inside += _inside(points, x, y)
    return inside / (side * side)


def _inside(points: tuple[Point, ...], x: float, y: float) -> bool:
    crossings = False
    for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1], strict=True):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            crossings = not crossings
    return crossings
