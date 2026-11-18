from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response

from sadu.modules.admin.interface.auth import Inspector
from sadu.modules.reports import api as reports
from sadu.modules.treatments import api as treatments
from sadu.shared.web import Session, State

router = APIRouter(tags=["reports"])

REPORTS_PER_USER_PER_HOUR = 30


@router.get("/maps/{map_id}/report.pdf", response_class=Response)
async def wall_report_pdf(map_id: UUID, user: Inspector, session: Session, state: State) -> Response:
    state.rate_limiter.check(f"report:{user.id}", REPORTS_PER_USER_PER_HOUR, 3600)
    catalog = treatments.catalog_at(state.settings.treatment_catalog_path)
    report = await reports.wall_report(session, state.store, map_id, catalog)
    pdf = await reports.wall_report_pdf(report)
    filename = f"athar-wall-report-{report.created_at:%Y-%m-%d}-{report.map_id[:8]}.pdf"
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )
