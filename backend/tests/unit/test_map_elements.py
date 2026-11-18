import pytest

from sadu.modules.mapping.domain.damage_map import CellSource, MapCell
from sadu.modules.mapping.domain.elements import (
    EditAction,
    Element,
    ElementEdit,
    apply_edits,
    element_from_json,
    element_json,
    elements_from_cells,
    location_label,
    measure,
)
from sadu.modules.mapping.domain.glossary import GLOSSARY, Geometry
from sadu.modules.mapping.domain.grid import CellRef, Grid, WallSize
from sadu.modules.mapping.domain.workflow import StepState, WorkflowFacts, workflow
from sadu.shared.vocabulary import DamageType, ModelConfidence, Severity

GRID = Grid(rows=4, cols=4)
WALL = WallSize(8.0, 4.0)


def cell(
    row: int, col: int, damage_type: DamageType, confidence: ModelConfidence = ModelConfidence.HIGH
) -> MapCell:
    return MapCell(CellRef(row, col), damage_type, Severity.MODERATE, confidence, CellSource.MODEL)


def element(damage_type: DamageType, points, damage_class=None) -> Element:
    return Element(
        "E1",
        damage_type,
        tuple(points),
        Severity.WATCH,
        ModelConfidence.HIGH,
        CellSource.EXPERT,
        damage_class,
    )


def test_the_glossary_covers_the_six_types_in_the_diriyah_brief():
    core = {t for t, entry in GLOSSARY.items() if entry.core}
    assert {
        DamageType.PLASTER_LOSS,
        DamageType.CRACK,
        DamageType.BASAL_EROSION,
        DamageType.RAIN_GULLY,
        DamageType.SALT_EFFLORESCENCE,
        DamageType.CAVITY,
    } <= core
    assert GLOSSARY[DamageType.CRACK].geometry is Geometry.LINE
    assert GLOSSARY[DamageType.CAVITY].geometry is Geometry.POINT
    assert GLOSSARY[DamageType.SALT_EFFLORESCENCE].geometry is Geometry.AREA


def test_areas_lengths_and_counts_are_measured_in_wall_metres():
    square = element(DamageType.PLASTER_LOSS, [(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)])
    crack = element(DamageType.CRACK, [(0.5, 0), (0.5, 1)], "under_1mm")
    hole = element(DamageType.CAVITY, [(0.2, 0.2)], "small")
    assert measure(square, WALL).area_m2 == 8.0
    assert measure(crack, WALL).length_m == 4.0
    assert measure(hole, WALL).count == 1


@pytest.mark.parametrize(
    ("damage_type", "points", "damage_class"),
    [
        (DamageType.CRACK, [(0.1, 0.1)], None),
        (DamageType.PLASTER_LOSS, [(0, 0), (1, 1)], None),
        (DamageType.CAVITY, [(0.1, 0.1), (0.2, 0.2)], None),
        (DamageType.CRACK, [(0, 0), (1.2, 1)], None),
        (DamageType.CRACK, [(0, 0), (1, 1)], "deep"),
        (DamageType.PLASTER_LOSS, [(0, 0), (1, 0), (1, 1)], "small"),
    ],
)
def test_shapes_that_break_the_glossary_are_refused(damage_type, points, damage_class):
    with pytest.raises(ValueError):
        element(damage_type, points, damage_class)


def test_model_cells_become_one_element_per_connected_patch():
    cells = [
        cell(0, 1, DamageType.CRACK),
        cell(1, 1, DamageType.CRACK),
        cell(2, 1, DamageType.CRACK, ModelConfidence.LOW),
        cell(3, 0, DamageType.BASAL_EROSION),
        cell(3, 1, DamageType.BASAL_EROSION),
        cell(1, 3, DamageType.CAVITY),
        cell(2, 3, DamageType.CAVITY),
    ]
    elements = elements_from_cells(cells, GRID)
    by_type: dict[DamageType, list[Element]] = {}
    for e in elements:
        by_type.setdefault(e.damage_type, []).append(e)
    [crack] = by_type[DamageType.CRACK]
    assert crack.points == ((0.375, 0.125), (0.375, 0.375), (0.375, 0.625))
    assert crack.confidence is ModelConfidence.LOW and crack.needs_review
    [base] = by_type[DamageType.BASAL_EROSION]
    assert measure(base, WALL).area_m2 == pytest.approx(4.0)
    assert len(by_type[DamageType.CAVITY]) == 2
    assert location_label(by_type[DamageType.CAVITY][0], GRID) == "B4"


def test_edits_keep_ids_stable_and_log_before_and_after():
    original = elements_from_cells([cell(0, 0, DamageType.PLASTER_LOSS), cell(3, 3, DamageType.CAVITY)], GRID)
    replacement = element(DamageType.PLASTER_LOSS, [(0, 0), (0.3, 0), (0.3, 0.3)])
    added = element(DamageType.RAIN_GULLY, [(0.6, 0), (0.6, 0.4)], "medium")
    result = apply_edits(
        original,
        [
            ElementEdit(EditAction.UPDATE, "E1", replacement),
            ElementEdit(EditAction.DELETE, "E2"),
            ElementEdit(EditAction.ADD, None, added),
        ],
    )
    assert [e.id for e in result.elements] == ["E1", "E3"]
    assert result.elements[0].points == replacement.points
    assert [entry["action"] for entry in result.log] == ["update", "delete", "add"]
    assert element_from_json(element_json(result.elements[1])) == result.elements[1]
    with pytest.raises(ValueError):
        apply_edits(original, [ElementEdit(EditAction.DELETE, "E9")])


def test_approval_waits_for_a_field_inspection():
    facts = WorkflowFacts(
        elements=3,
        low_confidence=1,
        treatments_matched=2,
        treatments_unmatched=0,
        material_lines=4,
        corrections=0,
        field_inspected=False,
        approved=False,
    )
    steps = workflow(facts)
    assert [s.number for s in steps] == list(range(1, 11))
    assert steps[3].state is StepState.FLAGGED
    assert steps[8].state is StepState.BLOCKED
    inspected = workflow(WorkflowFacts(**{**facts.__dict__, "field_inspected": True}))
    assert inspected[8].state is StepState.WAITING
