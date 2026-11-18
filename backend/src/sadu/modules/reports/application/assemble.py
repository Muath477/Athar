from datetime import datetime

from sadu.modules.mapping import api as mapping
from sadu.modules.reports.domain.wall_report import (
    ChangeLine,
    DamageTotal,
    MaterialLine,
    ReportCell,
    SourceLine,
    TreatmentLine,
    WallReport,
    damage_totals,
    material_totals,
    model_agreement,
)
from sadu.modules.treatments import api as treatments


def assemble_wall_report(
    view: mapping.MapView,
    *,
    site_name: str | None,
    previous: mapping.MapView | None,
    catalog: treatments.Catalog,
    overlay_jpeg: bytes,
    generated_at: datetime,
) -> WallReport:
    cell_area = view.grid.cell_area_m2(view.wall)
    cells = tuple(sorted((_cell(c) for c in view.cells), key=lambda c: (c.label[0], int(c.label[1:]))))
    plan = mapping.treatment_plan(view, catalog)
    treatment_lines = tuple(_treatment(item) for item in plan.items)
    changes = mapping.changes_between(previous, view) if previous else None
    cited = sorted({source_id for line in treatment_lines for source_id in line.source_ids})

    return WallReport(
        map_id=str(view.id),
        wall_name=view.wall_name,
        site_name=site_name,
        approved=view.status is mapping.MapStatus.APPROVED,
        approved_at=view.approved_at,
        created_at=view.created_at,
        generated_at=generated_at,
        width_m=view.wall.width_m,
        height_m=view.wall.height_m,
        rows=view.grid.rows,
        cols=view.grid.cols,
        cell_area_m2=cell_area,
        detector=view.detector,
        overlay_jpeg=overlay_jpeg,
        damage_colors={str(k): v for k, v in mapping.DAMAGE_COLORS.items()},
        cells=cells,
        totals=damage_totals(cells, cell_area),
        previous_approved_at=previous.approved_at if previous else None,
        changes=tuple(_change(c) for c in changes) if changes is not None else None,
        treatments=treatment_lines,
        unmatched=tuple(
            DamageTotal(str(a.damage_type), a.cells, a.area_m2, str(a.severity)) for a in plan.unmatched
        ),
        material_totals=material_totals(treatment_lines),
        catalog_version=plan.catalog_version,
        catalog_reviewed=plan.catalog_review_status is treatments.ReviewStatus.APPROVED,
        quantities_note_ar=plan.quantities_note_ar,
        sources=tuple(SourceLine(s, catalog.sources[s].title, catalog.sources[s].url) for s in cited),
        agreement=model_agreement((_cell(c) for c in view.model_cells), cells),
    )


def _cell(cell: mapping.MapCell) -> ReportCell:
    return ReportCell(cell.ref.label, str(cell.damage_type), str(cell.severity), str(cell.source))


def _change(change: mapping.CellChange) -> ChangeLine:
    return ChangeLine(
        label=change.ref.label,
        kind=str(change.kind),
        before=_cell(change.before) if change.before else None,
        after=_cell(change.after) if change.after else None,
    )


def _treatment(item: treatments.PlanItem) -> TreatmentLine:
    return TreatmentLine(
        title_ar=item.treatment.title_ar,
        damage_type=str(item.treatment.damage_type),
        severity=str(item.severity),
        cells=item.cells,
        area_m2=item.area_m2,
        steps_ar=item.treatment.steps_ar,
        materials=tuple(MaterialLine(m.name_ar, m.unit_ar, m.quantity) for m in item.materials),
        tools_ar=item.treatment.tools_ar,
        specialist_required=item.treatment.specialist_required,
        source_ids=item.treatment.source_ids,
    )
