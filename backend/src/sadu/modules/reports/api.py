import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.mapping import api as mapping
from sadu.modules.reports.application.assemble import assemble_wall_report
from sadu.modules.reports.application.exports import (
    CONDITION_HEADER,
    ELEMENTS_HEADER,
    condition_rows,
    element_rows,
)
from sadu.modules.reports.application.site_condition import SiteCondition, site_condition
from sadu.modules.reports.domain.wall_report import WallReport
from sadu.modules.reports.infrastructure.pdf import render_pdf, site_condition_html, wall_report_html
from sadu.modules.sites import api as sites
from sadu.modules.treatments import api as treatments
from sadu.shared.storage import ObjectStore

__all__ = [
    "CONDITION_HEADER",
    "ELEMENTS_HEADER",
    "SiteCondition",
    "WallReport",
    "condition_rows",
    "element_rows",
    "site_condition",
    "site_condition_pdf",
    "wall_report",
    "wall_report_pdf",
]


async def wall_report(
    session: AsyncSession, store: ObjectStore, map_id: UUID, catalog: treatments.Catalog
) -> WallReport:
    view = await mapping.get_map(session, map_id)
    site_name = (await sites.get_site(session, view.site_id)).name_ar if view.site_id else None
    return assemble_wall_report(
        view,
        site_name=site_name,
        previous=await mapping.previous_approved(session, view),
        catalog=catalog,
        overlay_jpeg=await mapping.damage_overlay(store, view),
        generated_at=datetime.now(UTC),
    )


async def wall_report_pdf(report: WallReport) -> bytes:
    return await asyncio.to_thread(render_pdf, wall_report_html(report))


async def site_condition_pdf(condition: SiteCondition) -> bytes:
    return await asyncio.to_thread(render_pdf, site_condition_html(condition))
