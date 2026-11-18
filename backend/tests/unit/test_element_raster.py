from sadu.modules.mapping.domain.damage_map import CellSource, MapCell
from sadu.modules.mapping.domain.elements import Element, elements_from_cells
from sadu.modules.mapping.domain.grid import CellRef, Grid
from sadu.modules.mapping.domain.raster import cells_from_elements
from sadu.shared.vocabulary import DamageType, ModelConfidence, Severity

GRID = Grid(4, 6)


def cell(label: str, damage_type: DamageType, severity: Severity = Severity.WATCH) -> MapCell:
    return MapCell(GRID.parse(label), damage_type, severity, ModelConfidence.HIGH, CellSource.MODEL)


def element(damage_type: DamageType, points, severity=Severity.WATCH) -> Element:
    return Element("E1", damage_type, tuple(points), severity, ModelConfidence.MEDIUM, CellSource.MODEL)


def labels(cells) -> list[str]:
    return [c.ref.label for c in cells]


def test_elements_drawn_from_cells_cover_the_same_cells_again():
    original = (
        cell("A1", DamageType.PLASTER_LOSS),
        cell("A2", DamageType.PLASTER_LOSS),
        cell("B1", DamageType.PLASTER_LOSS),
        cell("B4", DamageType.CRACK),
        cell("C5", DamageType.CRACK),
        cell("D6", DamageType.CRACK),
        cell("D2", DamageType.CAVITY),
    )
    redrawn = cells_from_elements(elements_from_cells(original, GRID), GRID)
    assert sorted(labels(redrawn)) == sorted(labels(original))
    assert {c.ref.label: c.damage_type for c in redrawn} == {c.ref.label: c.damage_type for c in original}


def test_a_polygon_takes_only_cells_it_covers_enough():
    corner = element(DamageType.SALT_EFFLORESCENCE, [(0.0, 0.0), (0.2, 0.0), (0.2, 0.3), (0.0, 0.3)])
    assert labels(cells_from_elements([corner], GRID)) == ["A1", "A2", "B1"]


def test_a_line_takes_every_cell_it_crosses_and_a_point_takes_one():
    crack = element(DamageType.CRACK, [(0.05, 0.1), (0.95, 0.1)])
    cavity = element(DamageType.CAVITY, [(1.0, 1.0)])
    cells = cells_from_elements([crack, cavity], GRID)
    assert labels(cells) == ["A1", "A2", "A3", "A4", "A5", "A6", "D6"]


def test_overlapping_elements_keep_the_most_severe_type_per_cell():
    loss = element(DamageType.PLASTER_LOSS, [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)])
    crack = element(DamageType.CRACK, [(0.05, 0.1), (0.3, 0.1)], Severity.URGENT)
    by_ref = {c.ref: c for c in cells_from_elements([loss, crack], GRID)}
    assert by_ref[CellRef(0, 0)].damage_type is DamageType.CRACK
    assert by_ref[CellRef(1, 1)].damage_type is DamageType.PLASTER_LOSS
