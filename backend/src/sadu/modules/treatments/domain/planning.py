import math
from collections.abc import Iterable
from dataclasses import dataclass

from sadu.modules.treatments.domain.models import Catalog, ReviewStatus, Treatment
from sadu.shared.vocabulary import DamageType, Severity


@dataclass(frozen=True)
class DamagedArea:
    damage_type: DamageType
    severity: Severity
    area_m2: float
    cells: int


@dataclass(frozen=True)
class MaterialNeed:
    name_ar: str
    name_en: str
    unit_ar: str
    quantity: float


@dataclass(frozen=True)
class PlanItem:
    treatment: Treatment
    severity: Severity
    area_m2: float
    cells: int
    materials: tuple[MaterialNeed, ...]


@dataclass(frozen=True)
class TreatmentPlan:
    catalog_version: str
    catalog_review_status: ReviewStatus
    quantities_note_ar: str
    items: tuple[PlanItem, ...]
    unmatched: tuple[DamagedArea, ...]

    @property
    def needs_specialist(self) -> bool:
        return any(item.treatment.specialist_required for item in self.items) or bool(self.unmatched)


def plan_treatments(areas: Iterable[DamagedArea], catalog: Catalog) -> TreatmentPlan:
    items: list[PlanItem] = []
    unmatched: list[DamagedArea] = []
    for area in sorted(areas, key=_most_urgent_first):
        treatment = catalog.treatment_for(area.damage_type, area.severity)
        if treatment is None:
            unmatched.append(area)
            continue
        needs = tuple(
            MaterialNeed(m.name_ar, m.name_en, m.unit_ar, round_up(m.per_m2 * area.area_m2))
            for m in treatment.materials
        )
        items.append(PlanItem(treatment, area.severity, round(area.area_m2, 2), area.cells, needs))
    return TreatmentPlan(
        catalog.version, catalog.review_status, catalog.quantities_note_ar, tuple(items), tuple(unmatched)
    )


def round_up(quantity: float, step: float = 0.1) -> float:
    return round(math.ceil(round(quantity / step, 6)) * step, 2)


def _most_urgent_first(area: DamagedArea) -> tuple[int, float]:
    return (-area.severity.rank, -area.area_m2)
