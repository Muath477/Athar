from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.mapping import api as mapping
from sadu.modules.sites import api as sites
from sadu.modules.treatments import api as treatments

SURVEY_DUE_AFTER = timedelta(days=180)


@dataclass(frozen=True)
class WallCondition:
    name_ar: str
    facade_id: UUID | None
    map_id: UUID | None
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


@dataclass(frozen=True)
class TypeTotal:
    damage_type: str
    elements: int
    area_m2: float
    urgent: int


@dataclass(frozen=True)
class MaterialTotal:
    name_ar: str
    unit_ar: str
    quantity: float


@dataclass(frozen=True)
class SiteCondition:
    site: sites.SiteView
    generated_at: datetime
    walls: tuple[WallCondition, ...]
    totals: tuple[TypeTotal, ...]
    materials: tuple[MaterialTotal, ...]
    catalog_reviewed: bool

    @property
    def urgent(self) -> int:
        return sum(w.urgent for w in self.walls)

    @property
    def walls_due(self) -> int:
        return sum(1 for w in self.walls if w.survey_due)

    @property
    def awaiting_approval(self) -> int:
        return sum(1 for w in self.walls if w.status == mapping.MapStatus.DRAFT)


async def site_condition(
    session: AsyncSession, site_id: UUID, catalog: treatments.Catalog, now: datetime
) -> SiteCondition:
    site = await sites.get_site(session, site_id)
    latest: dict[str, mapping.MapSummary] = {}
    for summary in await mapping.list_maps(session, site_id=site_id):
        key = str(summary.facade_id) if summary.facade_id else summary.wall_name
        latest.setdefault(key, summary)

    walls: list[WallCondition] = []
    totals: dict[str, list[float]] = defaultdict(lambda: [0, 0.0, 0])
    materials: dict[tuple[str, str], float] = defaultdict(float)
    for facade in await sites.list_facades(session, site_id):
        if str(facade.id) not in latest:
            walls.append(_unsurveyed(facade))
    for summary in latest.values():
        view = await mapping.get_map(session, summary.id)
        plan = mapping.treatment_plan(view, catalog)
        walls.append(_wall(view, plan, now))
        for element in view.elements:
            total = totals[element.damage_type]
            total[0] += 1
            total[1] += mapping.measure(element, view.wall).footprint_m2
            total[2] += element.severity == "urgent"
        if view.status is mapping.MapStatus.APPROVED:
            for item in plan.items:
                for need in item.materials:
                    materials[(need.name_ar, need.unit_ar)] += need.quantity

    return SiteCondition(
        site=site,
        generated_at=now,
        walls=tuple(sorted(walls, key=lambda w: (-w.urgent, not w.survey_due, w.name_ar))),
        totals=tuple(
            TypeTotal(t, int(v[0]), round(v[1], 2), int(v[2]))
            for t, v in sorted(totals.items(), key=lambda kv: (-kv[1][2], -kv[1][1]))
        ),
        materials=tuple(MaterialTotal(n, u, round(q, 1)) for (n, u), q in sorted(materials.items())),
        catalog_reviewed=catalog.review_status is treatments.ReviewStatus.APPROVED,
    )


def _unsurveyed(facade: sites.FacadeView) -> WallCondition:
    return WallCondition(
        name_ar=facade.name_ar,
        facade_id=facade.id,
        map_id=None,
        status="not_surveyed",
        surveyed_at=None,
        approved_at=None,
        field_inspected_at=None,
        elements=0,
        urgent=0,
        needs_review=0,
        damaged_area_m2=0.0,
        needs_specialist=False,
        survey_due=True,
    )


def _wall(view: mapping.MapView, plan: treatments.TreatmentPlan, now: datetime) -> WallCondition:
    return WallCondition(
        name_ar=view.wall_name,
        facade_id=view.facade_id,
        map_id=view.id,
        status=view.status,
        surveyed_at=view.created_at,
        approved_at=view.approved_at,
        field_inspected_at=view.field_inspected_at,
        elements=len(view.elements),
        urgent=sum(1 for e in view.elements if e.severity == "urgent"),
        needs_review=len(view.low_confidence),
        damaged_area_m2=view.damaged_area_m2,
        needs_specialist=plan.needs_specialist,
        survey_due=now - view.created_at > SURVEY_DUE_AFTER,
    )
