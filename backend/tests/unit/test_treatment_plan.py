from pathlib import Path

import pytest

from sadu.modules.mapping.domain.damage_map import MAP_DAMAGE_TYPES
from sadu.modules.treatments import api as treatments
from sadu.modules.treatments.domain.planning import round_up
from sadu.shared.vocabulary import DamageType, Severity

CATALOG_PATH = Path(__file__).resolve().parents[3] / "region-packs" / "treatments" / "earthen-najdi.json"


@pytest.fixture
def catalog() -> treatments.Catalog:
    return treatments.catalog_at(CATALOG_PATH)


def test_shipped_catalog_covers_every_map_damage_type_and_severity(catalog):
    missing = [
        (damage_type, severity)
        for damage_type in MAP_DAMAGE_TYPES
        for severity in Severity
        if catalog.treatment_for(damage_type, severity) is None
    ]
    assert missing == []


def test_shipped_catalog_is_marked_for_expert_review(catalog):
    assert catalog.review_status is treatments.ReviewStatus.DRAFT
    assert all(t.source_ids for t in catalog.treatments)


def test_plan_scales_materials_by_area_and_puts_urgent_work_first(catalog):
    plan = treatments.plan_treatments(
        [
            treatments.DamagedArea(DamageType.PLASTER_LOSS, Severity.MODERATE, 2.0, 4),
            treatments.DamagedArea(DamageType.CRACK, Severity.URGENT, 0.5, 1),
        ],
        catalog,
    )
    assert [item.treatment.code for item in plan.items] == ["crack-structural", "plaster-renew"]
    plaster = plan.items[1]
    earth = next(m for m in plaster.materials if m.name_en == "Matching earth")
    assert earth.quantity == pytest.approx(60.0)
    assert plan.needs_specialist


def test_areas_without_a_treatment_are_listed_as_unmatched():
    empty = treatments.Catalog("0", treatments.ReviewStatus.DRAFT, None, "", {}, ())
    area = treatments.DamagedArea(DamageType.CRACK, Severity.WATCH, 1.0, 1)
    plan = treatments.plan_treatments([area], empty)
    assert plan.items == ()
    assert plan.unmatched == (area,)
    assert plan.needs_specialist


def test_catalog_rejects_overlapping_treatments_and_unknown_sources():
    source = treatments.Source("s", "title", "https://example.org")
    first = treatments.Treatment(
        "a", DamageType.CRACK, frozenset({Severity.WATCH}), "t", ("step",), (), (), False, ("s",)
    )
    overlapping = treatments.Treatment(
        "b", DamageType.CRACK, frozenset({Severity.WATCH}), "t", ("step",), (), (), False, ("s",)
    )
    with pytest.raises(ValueError, match="Two treatments"):
        treatments.Catalog("0", treatments.ReviewStatus.DRAFT, None, "", {"s": source}, (first, overlapping))
    with pytest.raises(ValueError, match="unknown sources"):
        treatments.Catalog("0", treatments.ReviewStatus.DRAFT, None, "", {}, (first,))


@pytest.mark.parametrize(("quantity", "expected"), [(0.0, 0.0), (1.01, 1.1), (2.0, 2.0), (0.3, 0.3)])
def test_quantities_round_up_to_a_tenth(quantity, expected):
    assert round_up(quantity) == expected
