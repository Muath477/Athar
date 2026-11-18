from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from sadu.modules.mapping import api as mapping
from sadu.modules.treatments import api as treatments
from sadu.shared.storage import ObjectStore
from sadu.shared.vocabulary import DamageType, Severity


class NewMapMeta(BaseModel):
    facade_id: UUID | None = None
    site_id: UUID | None = None
    wall_name: str | None = Field(default=None, min_length=1, max_length=200)
    width_m: float | None = Field(default=None, gt=0, le=500)
    height_m: float | None = Field(default=None, gt=0, le=100)
    corners: list[list[float]] | None = None
    observation_id: UUID | None = None


class CorrectionIn(BaseModel):
    cell: str = Field(min_length=2, max_length=4)
    damage_type: DamageType
    severity: Severity = Severity.WATCH


class CorrectionsIn(BaseModel):
    corrections: list[CorrectionIn] = Field(min_length=1, max_length=400)


class ElementIn(BaseModel):
    damage_type: DamageType
    points: list[list[float]] = Field(min_length=1, max_length=200)
    severity: Severity = Severity.WATCH
    damage_class: str | None = Field(default=None, max_length=20)


class ElementEditIn(BaseModel):
    action: mapping.EditAction
    element_id: str | None = Field(default=None, max_length=10)
    element: ElementIn | None = None


class ElementEditsIn(BaseModel):
    edits: list[ElementEditIn] = Field(min_length=1, max_length=200)


class FieldInspectionIn(BaseModel):
    notes: str = Field(default="", max_length=2000)


class ElementOut(BaseModel):
    id: str
    damage_type: str
    geometry: str
    points: list[list[float]]
    severity: str
    confidence: str
    source: str
    damage_class: str | None
    area_m2: float
    length_m: float
    count: int
    location: str
    needs_review: bool


class GlossaryEntryOut(BaseModel):
    damage_type: str
    name_ar: str
    geometry: str
    measure_ar: str
    class_kind: str | None
    classes: list[str]
    color: str
    core: bool


class StepOut(BaseModel):
    number: int
    key: str
    title_ar: str
    actor: str
    criterion: str
    state: str
    output_ar: str


class CorrectionLogOut(BaseModel):
    at: str
    by: str
    action: str
    element_id: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class CellOut(BaseModel):
    cell: str
    row: int
    col: int
    damage_type: str
    severity: str
    confidence: str
    source: str


class MaterialNeedOut(BaseModel):
    name_ar: str
    unit_ar: str
    quantity: float


class SourceOut(BaseModel):
    title: str
    url: str


class PlanItemOut(BaseModel):
    code: str
    title_ar: str
    damage_type: str
    severity: str
    area_m2: float
    cells: int
    steps_ar: list[str]
    tools_ar: list[str]
    materials: list[MaterialNeedOut]
    specialist_required: bool
    sources: list[SourceOut]
    locations: list[str]


class UnmatchedOut(BaseModel):
    damage_type: str
    severity: str
    area_m2: float
    cells: int


class PlanOut(BaseModel):
    catalog_version: str
    review_status: str
    quantities_note_ar: str
    needs_specialist: bool
    items: list[PlanItemOut]
    unmatched: list[UnmatchedOut]


class ChangeOut(BaseModel):
    cell: str
    kind: str
    before_type: str | None
    before_severity: str | None
    after_type: str | None
    after_severity: str | None


class ChangesOut(BaseModel):
    previous_map_id: str
    previous_created_at: datetime
    comparable: bool
    items: list[ChangeOut]


class MapOut(BaseModel):
    id: str
    site_id: str | None
    facade_id: str | None
    wall_name: str
    width_m: float
    height_m: float
    rows: int
    cols: int
    cell_area_m2: float
    corners: list[list[float]]
    photo_url: str
    rectified_url: str
    rectified_width_px: int
    rectified_height_px: int
    detector: str
    detector_status: str
    summary_ar: str
    status: str
    created_at: datetime
    approved_at: datetime | None
    damaged_area_m2: float
    damage_types: list[str]
    cells: list[CellOut]
    elements: list[ElementOut]
    workflow: list[StepOut]
    correction_log: list[CorrectionLogOut]
    field_inspected_at: datetime | None
    field_notes: str
    treatment_plan: PlanOut
    changes: ChangesOut | None


class MapSummaryOut(BaseModel):
    id: str
    site_id: str | None
    facade_id: str | None
    wall_name: str
    status: str
    detector_status: str
    damaged_cells: int
    urgent_cells: int
    total_cells: int
    thumbnail_url: str
    created_at: datetime


class TypeScoreOut(BaseModel):
    damage_type: str
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float | None
    recall: float | None
    f1: float | None


class AccuracyOut(BaseModel):
    maps: int
    cells: int
    damaged_vs_sound_accuracy: float | None
    by_type: list[TypeScoreOut]


def map_out(
    view: mapping.MapView,
    store: ObjectStore,
    catalog: treatments.Catalog,
    previous: mapping.MapView | None,
) -> MapOut:
    plan = mapping.treatment_plan(view, catalog)
    return MapOut(
        id=str(view.id),
        site_id=_str_or_none(view.site_id),
        facade_id=_str_or_none(view.facade_id),
        wall_name=view.wall_name,
        width_m=view.wall.width_m,
        height_m=view.wall.height_m,
        rows=view.grid.rows,
        cols=view.grid.cols,
        cell_area_m2=round(view.grid.cell_area_m2(view.wall), 3),
        corners=view.corners,
        photo_url=store.presigned_url(view.photo_key),
        rectified_url=store.presigned_url(view.rectified_key),
        rectified_width_px=view.rectified_width_px,
        rectified_height_px=view.rectified_height_px,
        detector=view.detector,
        detector_status=view.detector_status,
        summary_ar=view.summary_ar,
        status=view.status,
        created_at=view.created_at,
        approved_at=view.approved_at,
        damaged_area_m2=round(view.damaged_area_m2, 2),
        damage_types=[t.value for t in mapping.MAP_DAMAGE_TYPES],
        cells=[cell_out(c) for c in view.cells],
        elements=[element_out(e, view) for e in view.elements],
        workflow=[step_out(step) for step in mapping.map_workflow(view, plan)],
        correction_log=[CorrectionLogOut(**_log_fields(entry)) for entry in view.correction_log],
        field_inspected_at=view.field_inspected_at,
        field_notes=view.field_notes,
        treatment_plan=plan_out(plan, catalog),
        changes=changes_out(previous, view) if previous is not None else None,
    )


def cell_out(cell: mapping.MapCell) -> CellOut:
    return CellOut(
        cell=cell.ref.label,
        row=cell.ref.row,
        col=cell.ref.col,
        damage_type=cell.damage_type,
        severity=cell.severity,
        confidence=cell.confidence,
        source=cell.source,
    )


def plan_out(plan: treatments.TreatmentPlan, catalog: treatments.Catalog) -> PlanOut:
    return PlanOut(
        catalog_version=plan.catalog_version,
        review_status=plan.catalog_review_status,
        quantities_note_ar=plan.quantities_note_ar,
        needs_specialist=plan.needs_specialist,
        items=[
            PlanItemOut(
                code=item.treatment.code,
                title_ar=item.treatment.title_ar,
                damage_type=item.treatment.damage_type,
                severity=item.severity,
                area_m2=item.area_m2,
                cells=item.cells,
                steps_ar=list(item.treatment.steps_ar),
                tools_ar=list(item.treatment.tools_ar),
                materials=[
                    MaterialNeedOut(name_ar=m.name_ar, unit_ar=m.unit_ar, quantity=m.quantity)
                    for m in item.materials
                ],
                specialist_required=item.treatment.specialist_required,
                locations=list(item.locations),
                sources=[
                    SourceOut(title=catalog.sources[s].title, url=catalog.sources[s].url)
                    for s in item.treatment.source_ids
                ],
            )
            for item in plan.items
        ],
        unmatched=[
            UnmatchedOut(
                damage_type=a.damage_type, severity=a.severity, area_m2=round(a.area_m2, 2), cells=a.cells
            )
            for a in plan.unmatched
        ],
    )


def changes_out(previous: mapping.MapView, current: mapping.MapView) -> ChangesOut:
    changes = mapping.changes_between(previous, current)
    return ChangesOut(
        previous_map_id=str(previous.id),
        previous_created_at=previous.created_at,
        comparable=changes is not None,
        items=[
            ChangeOut(
                cell=change.ref.label,
                kind=change.kind,
                before_type=change.before.damage_type if change.before else None,
                before_severity=change.before.severity if change.before else None,
                after_type=change.after.damage_type if change.after else None,
                after_severity=change.after.severity if change.after else None,
            )
            for change in changes or []
        ],
    )


def summary_out(summary: mapping.MapSummary, store: ObjectStore) -> MapSummaryOut:
    return MapSummaryOut(
        id=str(summary.id),
        site_id=_str_or_none(summary.site_id),
        facade_id=_str_or_none(summary.facade_id),
        wall_name=summary.wall_name,
        status=summary.status,
        detector_status=summary.detector_status,
        damaged_cells=summary.damaged_cells,
        urgent_cells=summary.urgent_cells,
        total_cells=summary.total_cells,
        thumbnail_url=store.presigned_url(summary.rectified_key),
        created_at=summary.created_at,
    )


def accuracy_out(score: mapping.MapScore) -> AccuracyOut:
    return AccuracyOut(
        maps=score.maps,
        cells=score.cells,
        damaged_vs_sound_accuracy=score.damaged_vs_sound_accuracy,
        by_type=[
            TypeScoreOut(
                damage_type=t.damage_type,
                true_positives=t.true_positives,
                false_positives=t.false_positives,
                false_negatives=t.false_negatives,
                precision=t.precision,
                recall=t.recall,
                f1=t.f1,
            )
            for t in score.by_type
        ],
    )


def _str_or_none(value: UUID | None) -> str | None:
    return str(value) if value is not None else None


def element_out(element: mapping.Element, view: mapping.MapView) -> ElementOut:
    size = mapping.measure(element, view.wall)
    return ElementOut(
        id=element.id,
        damage_type=element.damage_type,
        geometry=element.geometry,
        points=[[x, y] for x, y in element.points],
        severity=element.severity,
        confidence=element.confidence,
        source=element.source,
        damage_class=element.damage_class,
        area_m2=size.area_m2,
        length_m=size.length_m,
        count=size.count,
        location=mapping.location_label(element, view.grid),
        needs_review=element.needs_review,
    )


def glossary_out() -> list[GlossaryEntryOut]:
    return [
        GlossaryEntryOut(
            damage_type=entry.damage_type,
            name_ar=entry.name_ar,
            geometry=entry.geometry,
            measure_ar=entry.measure_ar,
            class_kind=entry.class_kind,
            classes=list(mapping.CLASS_VALUES[entry.class_kind]) if entry.class_kind else [],
            color=mapping.DAMAGE_COLORS[entry.damage_type],
            core=entry.core,
        )
        for entry in mapping.GLOSSARY.values()
    ]


def step_out(step: mapping.Step) -> StepOut:
    return StepOut(
        number=step.number,
        key=step.key,
        title_ar=step.title_ar,
        actor=step.actor,
        criterion=step.criterion,
        state=step.state,
        output_ar=step.output_ar,
    )


def _log_fields(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "at": str(entry.get("at", "")),
        "by": str(entry.get("by", "")),
        "action": str(entry.get("action", "")),
        "element_id": str(entry.get("element_id", "")),
        "before": entry.get("before"),
        "after": entry.get("after"),
    }
