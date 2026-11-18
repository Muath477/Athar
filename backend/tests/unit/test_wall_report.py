from datetime import UTC, datetime

import pytest

from sadu.modules.reports.domain import arabic
from sadu.modules.reports.domain.wall_report import (
    MaterialLine,
    ModelAgreement,
    ReportCell,
    TreatmentLine,
    damage_totals,
    material_totals,
    model_agreement,
)


def cell(
    label: str, damage_type: str = "crack", severity: str = "moderate", source: str = "model"
) -> ReportCell:
    return ReportCell(label, damage_type, severity, source)


def treatment(*materials: MaterialLine) -> TreatmentLine:
    return TreatmentLine("t", "crack", "moderate", 1, 1.0, ("step",), materials, (), False, ())


def test_totals_put_the_most_urgent_type_first_and_keep_its_worst_severity():
    totals = damage_totals(
        [cell("A1"), cell("A2"), cell("B1", "moisture", "urgent"), cell("C1", "crack", "watch")], 0.5
    )
    assert [(t.damage_type, t.cells, t.area_m2, t.worst_severity) for t in totals] == [
        ("moisture", 1, 0.5, "urgent"),
        ("crack", 3, 1.5, "moderate"),
    ]


def test_totals_of_an_empty_map_are_empty():
    assert damage_totals([], 0.5) == ()


def test_material_totals_add_the_same_material_across_treatments():
    lime = MaterialLine("جير", "كغ", 2.5)
    totals = material_totals(
        [treatment(lime), treatment(MaterialLine("جير", "كغ", 1.5), MaterialLine("طين", "كغ", 4))]
    )
    assert totals == (MaterialLine("جير", "كغ", 4.0), MaterialLine("طين", "كغ", 4.0))


def test_agreement_counts_what_the_expert_kept_changed_added_and_removed():
    proposed = [cell("A1"), cell("A2"), cell("A3")]
    final = [cell("A1"), cell("A2", "moisture"), cell("B9", source="expert")]
    assert model_agreement(proposed, final) == ModelAgreement(
        proposed=3, kept=1, changed=1, added=1, removed=1
    )


@pytest.mark.parametrize(
    ("value", "places", "expected"),
    [(12.0, 1, "١٢"), (1.25, 2, "١٫٢٥"), (0.0, 1, "٠"), (100.0, 1, "١٠٠"), (2.456, 1, "٢٫٥")],
)
def test_numbers_use_arabic_digits_without_trailing_zeros(value, places, expected):
    assert arabic.number(value, places) == expected


def test_dates_are_shown_in_riyadh_time():
    late_evening_utc = datetime(2026, 11, 18, 22, 30, tzinfo=UTC)
    assert arabic.date_ar(late_evening_utc) == "١٩ نوفمبر ٢٠٢٦م"
