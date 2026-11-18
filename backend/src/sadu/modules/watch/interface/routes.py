from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from sadu.modules.admin import api as admin
from sadu.modules.admin.interface.auth import Expert, Inspector
from sadu.modules.watch import api as watch
from sadu.shared.storage import ObjectStore
from sadu.shared.web import Session, State

router = APIRouter(tags=["watch"])

SCANS_PER_USER_PER_HOUR = 30


class SignalOut(BaseModel):
    threat: str
    zone: str
    changed_pixels: int
    zone_pixels: int
    area_m2: float


class ScanOut(BaseModel):
    id: str
    site_id: str
    created_at: datetime
    source: str
    is_sample: bool
    status: str
    baseline_start: date
    baseline_end: date
    recent_start: date
    recent_end: date
    baseline_scenes: int
    recent_scenes: int
    valid_share: float
    score: int
    level: str
    signals: list[SignalOut]
    before_url: str | None
    after_url: str | None
    change_url: str | None
    acknowledged_at: datetime | None
    ground_check_at: datetime | None
    mission_ids: list[str]


class LatLonOut(BaseModel):
    lat: float
    lon: float


class SiteRiskOut(BaseModel):
    site_id: str
    slug: str
    name_ar: str
    name_en: str
    building_type: str
    location: LatLonOut
    facades: int
    priority: float
    latest: ScanOut | None


class WatchOverviewOut(BaseModel):
    source: str
    is_sample: bool
    threat_colors: dict[str, str]
    sites: list[SiteRiskOut]


class GroundCheckOut(BaseModel):
    scan: ScanOut
    mission_ids: list[str]
    inspector_visit: bool


def scan_out(view: watch.ScanView, store: ObjectStore) -> ScanOut:
    def url(key: str | None) -> str | None:
        return store.presigned_url(key) if key else None

    return ScanOut(
        id=str(view.id),
        site_id=str(view.site_id),
        created_at=view.created_at,
        source=view.source,
        is_sample=view.is_sample,
        status=view.status,
        baseline_start=view.periods.baseline_start,
        baseline_end=view.periods.baseline_end,
        recent_start=view.periods.recent_start,
        recent_end=view.periods.recent_end,
        baseline_scenes=view.baseline_scenes,
        recent_scenes=view.recent_scenes,
        valid_share=view.valid_share,
        score=view.score,
        level=view.level,
        signals=[
            SignalOut(
                threat=s.threat,
                zone=s.zone,
                changed_pixels=s.changed_pixels,
                zone_pixels=s.zone_pixels,
                area_m2=s.area_m2,
            )
            for s in view.signals
        ],
        before_url=url(view.before_key),
        after_url=url(view.after_key),
        change_url=url(view.change_key),
        acknowledged_at=view.acknowledged_at,
        ground_check_at=view.ground_check_at,
        mission_ids=[str(m) for m in view.mission_ids],
    )


@router.get("/watch/sites")
async def watch_overview(_: Inspector, session: Session, state: State, request: Request) -> WatchOverviewOut:
    source: watch.SceneSource = request.app.state.scene_source
    ranked = await watch.rank_sites(session)
    return WatchOverviewOut(
        source=source.name,
        is_sample=source.is_sample,
        threat_colors={str(k): v for k, v in watch.THREAT_COLORS.items()},
        sites=[
            SiteRiskOut(
                site_id=str(r.site.id),
                slug=r.site.slug,
                name_ar=r.site.name_ar,
                name_en=r.site.name_en,
                building_type=r.site.building_type,
                location=LatLonOut(lat=r.site.location.lat, lon=r.site.location.lon),
                facades=r.facades,
                priority=round(r.priority, 1),
                latest=scan_out(r.latest, state.store) if r.latest else None,
            )
            for r in ranked
        ],
    )


@router.get("/watch/sites/{site_id}/scans")
async def list_scans(site_id: UUID, _: Inspector, session: Session, state: State) -> list[ScanOut]:
    return [scan_out(v, state.store) for v in await watch.site_scans(session, site_id)]


@router.post("/watch/sites/{site_id}/scans", status_code=201)
async def scan_now(
    site_id: UUID, user: Inspector, session: Session, state: State, request: Request
) -> ScanOut:
    state.rate_limiter.check(f"watch-scan:{user.id}", SCANS_PER_USER_PER_HOUR, 3600)
    view = await watch.scan_site(session, state.store, request.app.state.scene_source, site_id)
    await admin.audit(
        session,
        actor_id=user.id,
        action="watch.scan",
        target_type="site",
        target_id=str(site_id),
        request_id=getattr(request.state, "request_id", None),
    )
    return scan_out(view, state.store)


@router.post("/watch/scans/{scan_id}/acknowledge")
async def acknowledge(scan_id: UUID, user: Expert, session: Session, state: State) -> ScanOut:
    return scan_out(await watch.acknowledge(session, scan_id, user.id), state.store)


@router.post("/watch/scans/{scan_id}/ground-check")
async def ground_check(
    scan_id: UUID, user: Inspector, session: Session, state: State, request: Request
) -> GroundCheckOut:
    result = await watch.request_ground_check(session, scan_id)
    await admin.audit(
        session,
        actor_id=user.id,
        action="watch.ground_check",
        target_type="site_scan",
        target_id=str(scan_id),
        details={"missions": [str(m.id) for m in result.missions]},
        request_id=getattr(request.state, "request_id", None),
    )
    return GroundCheckOut(
        scan=scan_out(result.scan, state.store),
        mission_ids=[str(m.id) for m in result.missions],
        inspector_visit=result.inspector_visit,
    )
