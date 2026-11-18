from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.admin import api as admin
from sadu.modules.admin.interface.auth import AuditReader, Exporter, Staff
from sadu.modules.mapping import api as mapping
from sadu.modules.reports import api as reports
from sadu.modules.treatments import api as treatments
from sadu.shared.tabular import csv_download
from sadu.shared.web import AppState, Session, State

router = APIRouter(tags=["reports"])

REPORTS_PER_USER_PER_HOUR = 30


class WallConditionOut(BaseModel):
    name_ar: str
    facade_id: str | None
    map_id: str | None
    status: str
    surveyed_at: datetime | None
    approved_at: datetime | None
    field_inspected_at: datetime | None
    elements: int
    urgent: int
    needs_review: int
    damaged_area_m2: float
    needs_specialist: bool
    survey_due: bool
    pending_draft_id: str | None


class TypeTotalOut(BaseModel):
    damage_type: str
    elements: int
    area_m2: float
    urgent: int


class MaterialTotalOut(BaseModel):
    name_ar: str
    unit_ar: str
    quantity: float


class SiteConditionOut(BaseModel):
    site_id: str
    name_ar: str
    building_type: str
    field_photography_permitted: bool
    generated_at: datetime
    urgent: int
    walls_due: int
    awaiting_approval: int
    catalog_reviewed: bool
    walls: list[WallConditionOut]
    totals: list[TypeTotalOut]
    materials: list[MaterialTotalOut]


class RatioOut(BaseModel):
    hits: int
    total: int
    value: float | None


class QualityOut(BaseModel):
    findings_with_evidence: RatioOut
    maps_with_evidence: RatioOut
    photos_held_back: RatioOut
    findings_held_for_specialist: RatioOut
    specialist_rejections: RatioOut
    maps_corrected_by_specialist: RatioOut
    every_report_has_evidence: bool | None
    evidence_target: float


def _ratio_out(ratio: reports.Ratio) -> RatioOut:
    return RatioOut(hits=ratio.hits, total=ratio.total, value=ratio.value)


@router.get("/reports/quality")
async def quality(_: AuditReader, session: Session) -> QualityOut:
    report = await reports.quality_report(session)
    return QualityOut(
        findings_with_evidence=_ratio_out(report.findings_with_evidence),
        maps_with_evidence=_ratio_out(report.maps_with_evidence),
        photos_held_back=_ratio_out(report.photos_held_back),
        findings_held_for_specialist=_ratio_out(report.findings_held_for_specialist),
        specialist_rejections=_ratio_out(report.specialist_rejections),
        maps_corrected_by_specialist=_ratio_out(report.maps_corrected_by_specialist),
        every_report_has_evidence=report.every_report_has_evidence,
        evidence_target=reports.EVIDENCE_TARGET,
    )


@router.get("/sites/{site_id}/condition")
async def site_condition(site_id: UUID, user: Staff, session: Session, state: State) -> SiteConditionOut:
    condition = await _condition(session, state, site_id, user)
    return SiteConditionOut(
        site_id=str(condition.site.id),
        name_ar=condition.site.name_ar,
        building_type=condition.site.building_type,
        field_photography_permitted=condition.site.field_photography_permitted,
        generated_at=condition.generated_at,
        urgent=condition.urgent,
        walls_due=condition.walls_due,
        awaiting_approval=condition.awaiting_approval,
        catalog_reviewed=condition.catalog_reviewed,
        walls=[
            WallConditionOut(
                name_ar=w.name_ar,
                facade_id=str(w.facade_id) if w.facade_id else None,
                map_id=str(w.map_id) if w.map_id else None,
                status=w.status,
                surveyed_at=w.surveyed_at,
                approved_at=w.approved_at,
                field_inspected_at=w.field_inspected_at,
                elements=w.elements,
                urgent=w.urgent,
                needs_review=w.needs_review,
                damaged_area_m2=w.damaged_area_m2,
                needs_specialist=w.needs_specialist,
                survey_due=w.survey_due,
                pending_draft_id=str(w.pending_draft) if w.pending_draft else None,
            )
            for w in condition.walls
        ],
        totals=[TypeTotalOut(**t.__dict__) for t in condition.totals],
        materials=[MaterialTotalOut(**m.__dict__) for m in condition.materials],
    )


@router.get("/sites/{site_id}/condition.csv", response_class=Response)
async def site_condition_csv(site_id: UUID, user: Exporter, session: Session, state: State) -> Response:
    condition = await _condition(session, state, site_id, user)
    filename = f"athar-condition-{condition.site.slug}-{condition.generated_at:%Y-%m-%d}.csv"
    return csv_download(filename, reports.CONDITION_HEADER, reports.condition_rows(condition))


@router.get("/sites/{site_id}/condition.pdf", response_class=Response)
async def site_condition_pdf(site_id: UUID, user: Exporter, session: Session, state: State) -> Response:
    state.rate_limiter.check(f"report:{user.id}", REPORTS_PER_USER_PER_HOUR, 3600)
    condition = await _condition(session, state, site_id, user)
    pdf = await reports.site_condition_pdf(condition)
    filename = f"athar-condition-{condition.site.slug}-{condition.generated_at:%Y-%m-%d}.pdf"
    return _pdf_download(pdf, filename)


@router.get("/maps/{map_id}/elements.csv", response_class=Response)
async def map_elements_csv(map_id: UUID, user: Exporter, session: Session) -> Response:
    view = await mapping.get_map(session, map_id)
    admin.ensure_sees_site(user, view.site_id)
    filename = f"athar-elements-{view.created_at:%Y-%m-%d}-{str(view.id)[:8]}.csv"
    return csv_download(filename, reports.ELEMENTS_HEADER, reports.element_rows(view))


@router.get("/maps/{map_id}/report.pdf", response_class=Response)
async def wall_report_pdf(map_id: UUID, user: Staff, session: Session, state: State) -> Response:
    state.rate_limiter.check(f"report:{user.id}", REPORTS_PER_USER_PER_HOUR, 3600)
    admin.ensure_sees_site(user, (await mapping.get_map(session, map_id)).site_id)
    catalog = treatments.catalog_at(state.settings.treatment_catalog_path)
    report = await reports.wall_report(session, state.store, map_id, catalog)
    pdf = await reports.wall_report_pdf(report)
    filename = f"athar-wall-report-{report.created_at:%Y-%m-%d}-{report.map_id[:8]}.pdf"
    return _pdf_download(pdf, filename)


async def _condition(
    session: AsyncSession, state: AppState, site_id: UUID, user: admin.UserView
) -> reports.SiteCondition:
    admin.ensure_sees_site(user, site_id)
    catalog = treatments.catalog_at(state.settings.treatment_catalog_path)
    return await reports.site_condition(session, site_id, catalog, datetime.now(UTC))


def _pdf_download(pdf: bytes, filename: str) -> Response:
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )
