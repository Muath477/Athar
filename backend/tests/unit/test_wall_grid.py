import pytest

from sadu.modules.mapping.domain.grid import Box, CellRef, Grid, WallSize
from sadu.modules.mapping.domain.quad import Quad


@pytest.mark.parametrize(
    ("width_m", "height_m", "expected_cols"),
    [(10, 6, 13), (6, 6, 8), (2, 6, 4), (60, 3, 16)],
)
def test_grid_columns_follow_wall_aspect_within_limits(width_m, height_m, expected_cols):
    assert Grid.for_wall(WallSize(width_m, height_m), rows=8).cols == expected_cols


def test_cell_labels_round_trip():
    grid = Grid(8, 12)
    assert CellRef(1, 3).label == "B4"
    assert grid.parse("b4") == CellRef(1, 3)
    assert grid.parse("H12") == CellRef(7, 11)


@pytest.mark.parametrize("label", ["", "A", "4B", "I1", "A13", "A0", "AA1"])
def test_parse_rejects_labels_outside_the_grid(label):
    with pytest.raises(ValueError):
        Grid(8, 12).parse(label)


def test_cell_area_splits_the_wall_evenly():
    assert Grid(8, 10).cell_area_m2(WallSize(10, 8)) == pytest.approx(1.0)


def test_box_coverage_reports_fraction_of_each_cell():
    coverage = Grid(2, 2).coverage(Box(0.25, 0.0, 0.75, 0.5))
    assert coverage == {CellRef(0, 0): pytest.approx(0.5), CellRef(0, 1): pytest.approx(0.5)}


def test_box_touching_a_cell_edge_does_not_cover_it():
    assert set(Grid(2, 2).coverage(Box(0.0, 0.0, 0.5, 0.5))) == {CellRef(0, 0)}


def test_box_must_have_positive_size_inside_the_unit_square():
    with pytest.raises(ValueError):
        Box(0.5, 0.5, 0.5, 0.9)
    assert Box.clipped(-0.2, 0.1, 1.4, 0.3) == Box(0.0, 0.1, 1.0, 0.3)
    assert Box.clipped(1.2, 0.1, 1.4, 0.3) is None


def test_full_frame_quad_is_valid():
    assert Quad.full_frame().area == pytest.approx(1.0)


@pytest.mark.parametrize(
    "corners",
    [
        [[0, 0], [0, 1], [1, 1], [1, 0]],
        [[0, 0], [1, 1], [1, 0], [0, 1]],
        [[0.4, 0.4], [0.5, 0.4], [0.5, 0.5], [0.4, 0.5]],
        [[0, 0], [1.2, 0], [1, 1], [0, 1]],
        [[0, 0], [1, 0], [1, 1]],
    ],
    ids=["counter-clockwise", "self-crossing", "too-small", "outside-photo", "three-corners"],
)
def test_quad_rejects_bad_outlines(corners):
    with pytest.raises(ValueError):
        Quad.from_list(corners)


def test_quad_accepts_a_perspective_outline():
    quad = Quad.from_list([[0.1, 0.2], [0.9, 0.1], [0.95, 0.9], [0.05, 0.85]])
    assert quad.as_list()[2] == [0.95, 0.9]
