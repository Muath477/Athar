from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

SEVERITY_RANK = {"watch": 0, "moderate": 1, "urgent": 2}
LINE_BAND_M = 0.1
POINT_AREA_M2 = 0.04


@dataclass(frozen=True)
class ReportCell:
    label: str
    damage_type: str
    severity: str
    source: str


@dataclass(frozen=True)
class ElementLine:
    id: str
    damage_type: str
    location: str
    area_m2: float
    length_m: float
    count: int
    damage_class: str | None
    severity: str
    source: str
    needs_review: bool


@dataclass(frozen=True)
class DamageTotal:
    damage_type: str
    cells: int
    area_m2: float
    worst_severity: str


@dataclass(frozen=True)
class ChangeLine:
    label: str
    kind: str
    before: ReportCell | None
    after: ReportCell | None


@dataclass(frozen=True)
class MaterialLine:
    name_ar: str
    unit_ar: str
    quantity: float


@dataclass(frozen=True)
class TreatmentLine:
    title_ar: str
    damage_type: str
    severity: str
    cells: int
    area_m2: float
    steps_ar: tuple[str, ...]
    materials: tuple[MaterialLine, ...]
    tools_ar: tuple[str, ...]
    specialist_required: bool
    source_ids: tuple[str, ...]
    locations: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceLine:
    id: str
    title: str
    url: str


@dataclass(frozen=True)
class ModelAgreement:
    proposed: int
    kept: int
    changed: int
    added: int
    removed: int


@dataclass(frozen=True)
class WallReport:
    map_id: str
    wall_name: str
    site_name: str | None
    approved: bool
    approved_at: datetime | None
    created_at: datetime
    generated_at: datetime
    width_m: float
    height_m: float
    rows: int
    cols: int
    cell_area_m2: float
    detector: str
    overlay_jpeg: bytes
    damage_colors: dict[str, str]
    cells: tuple[ReportCell, ...]
    totals: tuple[DamageTotal, ...]
    previous_approved_at: datetime | None
    changes: tuple[ChangeLine, ...] | None
    treatments: tuple[TreatmentLine, ...]
    unmatched: tuple[DamageTotal, ...]
    material_totals: tuple[MaterialLine, ...]
    catalog_version: str
    catalog_reviewed: bool
    quantities_note_ar: str
    sources: tuple[SourceLine, ...]
    agreement: ModelAgreement
    elements: tuple[ElementLine, ...] = ()
    field_inspected_at: datetime | None = None
    field_notes: str = ""
    corrections_logged: int = 0

    @property
    def wall_area_m2(self) -> float:
        return self.width_m * self.height_m

    @property
    def damaged_area_m2(self) -> float:
        if self.elements:
            return sum(e.area_m2 + e.length_m * LINE_BAND_M + e.count * POINT_AREA_M2 for e in self.elements)
        return len(self.cells) * self.cell_area_m2

    @property
    def needs_review(self) -> int:
        return sum(1 for e in self.elements if e.needs_review)

    @property
    def damaged_share(self) -> float:
        return self.damaged_area_m2 / self.wall_area_m2 if self.wall_area_m2 else 0.0

    @property
    def urgent_cells(self) -> int:
        return sum(1 for cell in self.cells if cell.severity == "urgent")

    @property
    def needs_specialist(self) -> bool:
        return any(t.specialist_required for t in self.treatments) or bool(self.unmatched)


def damage_totals(cells: Iterable[ReportCell], cell_area_m2: float) -> tuple[DamageTotal, ...]:
    grouped: dict[str, list[ReportCell]] = {}
    for cell in cells:
        grouped.setdefault(cell.damage_type, []).append(cell)
    totals = [
        DamageTotal(
            damage_type=damage_type,
            cells=len(group),
            area_m2=len(group) * cell_area_m2,
            worst_severity=max((c.severity for c in group), key=SEVERITY_RANK.__getitem__),
        )
        for damage_type, group in grouped.items()
    ]
    return tuple(sorted(totals, key=lambda t: (-SEVERITY_RANK[t.worst_severity], -t.cells, t.damage_type)))


def element_totals(elements: Iterable[ElementLine]) -> tuple[DamageTotal, ...]:
    grouped: dict[str, list[ElementLine]] = {}
    for element in elements:
        grouped.setdefault(element.damage_type, []).append(element)
    totals = [
        DamageTotal(
            damage_type=damage_type,
            cells=len(group),
            area_m2=sum(e.area_m2 + e.length_m * LINE_BAND_M + e.count * POINT_AREA_M2 for e in group),
            worst_severity=max((e.severity for e in group), key=SEVERITY_RANK.__getitem__),
        )
        for damage_type, group in grouped.items()
    ]
    return tuple(sorted(totals, key=lambda t: (-SEVERITY_RANK[t.worst_severity], -t.cells, t.damage_type)))


def material_totals(treatments: Iterable[TreatmentLine]) -> tuple[MaterialLine, ...]:
    summed: dict[tuple[str, str], float] = {}
    for treatment in treatments:
        for material in treatment.materials:
            key = (material.name_ar, material.unit_ar)
            summed[key] = summed.get(key, 0.0) + material.quantity
    return tuple(MaterialLine(name, unit, quantity) for (name, unit), quantity in sorted(summed.items()))


def model_agreement(proposed: Iterable[ReportCell], final: Iterable[ReportCell]) -> ModelAgreement:
    by_label = {cell.label: cell for cell in proposed}
    final_by_label = {cell.label: cell for cell in final}
    kept = changed = 0
    for label, cell in final_by_label.items():
        suggestion = by_label.get(label)
        if suggestion is None:
            continue
        if (suggestion.damage_type, suggestion.severity) == (cell.damage_type, cell.severity):
            kept += 1
        else:
            changed += 1
    return ModelAgreement(
        proposed=len(by_label),
        kept=kept,
        changed=changed,
        added=len(final_by_label.keys() - by_label.keys()),
        removed=len(by_label.keys() - final_by_label.keys()),
    )
