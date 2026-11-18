import pytest

from sadu.modules.mapping.domain.changes import ChangeKind, compare_maps
from sadu.modules.mapping.domain.damage_map import (
    CellCorrection,
    CellSource,
    MapCell,
    apply_corrections,
    keep_strongest,
    tally_areas,
)
from sadu.modules.mapping.domain.grid import CellRef, Grid, WallSize
from sadu.modules.mapping.domain.scoring import ScoredPair, score_maps
from sadu.shared.vocabulary import DamageType, ModelConfidence, Severity

GRID = Grid(4, 4)


def cell(label, damage_type=DamageType.CRACK, severity=Severity.WATCH, confidence=ModelConfidence.MEDIUM):
    return MapCell(GRID.parse(label), damage_type, severity, confidence, CellSource.MODEL)


def test_map_cells_accept_only_wall_damage_types():
    with pytest.raises(ValueError):
        cell("A1", DamageType.NEW_CONSTRUCTION)


def test_corrections_set_and_clear_cells():
    cells = (cell("A1"), cell("B2"))
    corrected = apply_corrections(
        cells,
        [
            CellCorrection(CellRef(0, 0), DamageType.NONE, Severity.WATCH),
            CellCorrection(CellRef(2, 2), DamageType.MOISTURE, Severity.URGENT),
        ],
        GRID,
    )
    assert [(c.ref.label, c.damage_type, c.source) for c in corrected] == [
        ("B2", DamageType.CRACK, CellSource.MODEL),
        ("C3", DamageType.MOISTURE, CellSource.EXPERT),
    ]
    assert corrected[1].confidence is ModelConfidence.HIGH


def test_corrections_outside_the_grid_are_rejected():
    with pytest.raises(ValueError):
        apply_corrections((), [CellCorrection(CellRef(4, 0), DamageType.CRACK, Severity.WATCH)], GRID)


def test_strongest_finding_wins_a_cell():
    kept = keep_strongest(
        [
            cell("A1", DamageType.CRACK, Severity.WATCH, ModelConfidence.HIGH),
            cell("A1", DamageType.MOISTURE, Severity.MODERATE, ModelConfidence.LOW),
            cell("A1", DamageType.PLASTER_LOSS, Severity.MODERATE, ModelConfidence.MEDIUM),
        ]
    )
    assert [c.damage_type for c in kept] == [DamageType.PLASTER_LOSS]


def test_areas_are_tallied_by_type_and_severity_most_urgent_first():
    tallies = tally_areas(
        [cell("A1"), cell("A2"), cell("B1", DamageType.MOISTURE, Severity.URGENT)], GRID, WallSize(8, 4)
    )
    assert [(t.damage_type, t.severity, t.cells, t.area_m2) for t in tallies] == [
        (DamageType.MOISTURE, Severity.URGENT, 1, 2.0),
        (DamageType.CRACK, Severity.WATCH, 2, 4.0),
    ]


def test_compare_maps_names_each_kind_of_change():
    before = [cell("A1"), cell("A2"), cell("A3", severity=Severity.MODERATE), cell("A4")]
    after = [
        cell("A1", severity=Severity.URGENT),
        cell("A2", DamageType.MOISTURE),
        cell("A3"),
        cell("B1"),
    ]
    kinds = {c.ref.label: c.kind for c in compare_maps(before, after)}
    assert kinds == {
        "A1": ChangeKind.WORSE,
        "A2": ChangeKind.RETYPED,
        "A3": ChangeKind.IMPROVED,
        "A4": ChangeKind.RESOLVED,
        "B1": ChangeKind.NEW,
    }


def test_unchanged_cells_are_not_reported():
    assert compare_maps([cell("A1")], [cell("A1")]) == []


def test_scoring_counts_cell_agreement_per_type():
    crack, moisture = DamageType.CRACK, DamageType.MOISTURE
    predicted = {CellRef(0, 0): crack, CellRef(0, 1): crack, CellRef(0, 2): moisture}
    expected = {CellRef(0, 0): crack, CellRef(0, 2): crack, CellRef(1, 0): moisture}
    score = score_maps([ScoredPair(16, predicted, expected)])
    by_type = {s.damage_type: s for s in score.by_type}

    assert (by_type[crack].true_positives, by_type[crack].false_positives) == (1, 1)
    assert by_type[crack].false_negatives == 1
    assert by_type[crack].precision == pytest.approx(0.5)
    assert by_type[moisture].recall == 0.0
    assert by_type[DamageType.GRAFFITI].precision is None
    assert score.damaged_vs_sound_accuracy == pytest.approx(14 / 16)


def test_scoring_with_no_maps_has_no_accuracy():
    assert score_maps([]).damaged_vs_sound_accuracy is None
