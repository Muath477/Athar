import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.missions import api as missions
from sadu.modules.sites import api as sites
from sadu.modules.watch.application.ports import SceneSource, SceneSourceUnavailable, WatchArea
from sadu.modules.watch.application.screening import BUFFER_M, Periods, Screening, screen
from sadu.modules.watch.domain.change import THREAT_COLORS, ChangeRules, Signal, Threat, Zone
from sadu.modules.watch.domain.geometry import LatLon, window_for
from sadu.modules.watch.domain.risk import Risk, RiskLevel, priority
from sadu.modules.watch.infrastructure.disabled_source import DisabledSceneSource
from sadu.modules.watch.infrastructure.earth_search import EarthSearchSceneSource
from sadu.modules.watch.infrastructure.evidence import render
from sadu.modules.watch.infrastructure.orm import SiteScanRow
from sadu.modules.watch.infrastructure.sample_source import SampleSceneSource
from sadu.shared.config import SceneSourceKind, Settings
from sadu.shared.errors import Conflict, NotFound
from sadu.shared.storage import ObjectStore, new_object_key

__all__ = [
    "THREAT_COLORS",
    "GroundCheck",
    "RiskLevel",
    "ScanStatus",
    "ScanView",
    "SceneSource",
    "SiteRisk",
    "Threat",
    "Zone",
    "acknowledge",
    "build_scene_source",
    "due_sites",
    "rank_sites",
    "request_ground_check",
    "scan_site",
    "site_scans",
]

WORLD_HERITAGE_TYPE = "world_heritage"
GROUND_CHECK_FACADES = 3
LEVEL_RANK = {
    RiskLevel.UNKNOWN: 0,
    RiskLevel.STABLE: 1,
    RiskLevel.WATCH: 2,
    RiskLevel.MODERATE: 3,
    RiskLevel.URGENT: 4,
}


class ScanStatus(StrEnum):
    OK = "ok"
    INSUFFICIENT_DATA = "insufficient_data"
    SOURCE_UNAVAILABLE = "source_unavailable"


@dataclass(frozen=True)
class SignalView:
    threat: Threat
    zone: Zone
    changed_pixels: int
    zone_pixels: int
    area_m2: float


@dataclass(frozen=True)
class ScanView:
    id: UUID
    site_id: UUID
    created_at: datetime
    source: str
    is_sample: bool
    status: ScanStatus
    periods: Periods
    baseline_scenes: int
    recent_scenes: int
    valid_share: float
    score: int
    level: RiskLevel
    signals: tuple[SignalView, ...]
    before_key: str | None
    after_key: str | None
    change_key: str | None
    acknowledged_at: datetime | None
    ground_check_at: datetime | None
    mission_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class SiteRisk:
    site: sites.SiteView
    facades: int
    latest: ScanView | None
    priority: float


@dataclass(frozen=True)
class GroundCheck:
    scan: ScanView
    missions: tuple[missions.MissionView, ...]
    inspector_visit: bool


def build_scene_source(settings: Settings) -> SceneSource:
    match settings.sadu_scene_source:
        case SceneSourceKind.EARTH_SEARCH:
            return EarthSearchSceneSource(settings.sadu_scene_search_url)
        case SceneSourceKind.SAMPLE:
            return SampleSceneSource(settings.watch_sample_events_path)
        case SceneSourceKind.NONE:
            return DisabledSceneSource()


async def due_sites(session: AsyncSession, interval: timedelta, now: datetime | None = None) -> list[UUID]:
    cutoff = (now or datetime.now(UTC)) - interval
    due = []
    for site in await sites.list_sites(session):
        latest = next(iter(await site_scans(session, site.id, limit=1)), None)
        if latest is None or latest.created_at <= cutoff:
            due.append(site.id)
    return due


async def watch_area(session: AsyncSession, site_id: UUID) -> WatchArea:
    site = await sites.get_site(session, site_id)
    center = LatLon(site.location.lat, site.location.lon)
    boundary = [LatLon(p.lat, p.lon) for p in site.boundary]
    return WatchArea(site.id, site.slug, center, boundary, window_for(boundary, center, BUFFER_M))


async def scan_site(
    session: AsyncSession,
    store: ObjectStore,
    source: SceneSource,
    site_id: UUID,
    *,
    today: date | None = None,
    rules: ChangeRules | None = None,
) -> ScanView:
    area = await watch_area(session, site_id)
    today = today or datetime.now(UTC).date()
    try:
        screening = await screen(source, area, today, rules or ChangeRules())
    except SceneSourceUnavailable:
        return await _save_unavailable(session, source, site_id, Periods.ending(today))
    keys = await _store_evidence(store, screening)
    return await _save(session, source, site_id, screening, keys)


async def site_scans(session: AsyncSession, site_id: UUID, limit: int = 20) -> list[ScanView]:
    rows = await session.scalars(
        select(SiteScanRow)
        .where(SiteScanRow.site_id == site_id)
        .order_by(SiteScanRow.created_at.desc())
        .limit(limit)
    )
    return [_view(row) for row in rows]


async def rank_sites(session: AsyncSession) -> list[SiteRisk]:
    ranked = []
    for site in await sites.list_sites(session):
        latest = next(iter(await site_scans(session, site.id, limit=1)), None)
        score = 0.0
        if latest is not None and latest.status is ScanStatus.OK:
            score = priority_of(latest, world_heritage=site.building_type == WORLD_HERITAGE_TYPE)
        facades = len(await sites.list_facades(session, site.id))
        ranked.append(SiteRisk(site, facades, latest, score))
    return sorted(
        ranked, key=lambda r: (-_level_rank(r.latest), -r.priority, r.latest is None, r.site.name_ar)
    )


def _level_rank(scan: ScanView | None) -> int:
    if scan is None or scan.status is not ScanStatus.OK:
        return 0
    return LEVEL_RANK[scan.level]


def priority_of(scan: ScanView, *, world_heritage: bool) -> float:
    return priority(Risk(scan.score, scan.level, ()), world_heritage=world_heritage)


async def acknowledge(session: AsyncSession, scan_id: UUID, user_id: UUID) -> ScanView:
    row = await _row(session, scan_id)
    if row.acknowledged_at is None:
        row.acknowledged_by = user_id
        row.acknowledged_at = datetime.now(UTC)
    return _view(row)


async def request_ground_check(session: AsyncSession, scan_id: UUID) -> GroundCheck:
    row = await _row(session, scan_id)
    opened = []
    facades = await sites.list_facades(session, row.site_id)
    for facade in facades[:GROUND_CHECK_FACADES]:
        try:
            opened.append(
                await missions.create_mission(session, facade.id, missions.MissionReason.SATELLITE_ALERT)
            )
        except Conflict:
            continue
    row.ground_check_at = datetime.now(UTC)
    row.mission_ids = [*row.mission_ids, *(str(m.id) for m in opened)]
    await session.flush()
    return GroundCheck(_view(row), tuple(opened), inspector_visit=not facades)


async def _store_evidence(store: ObjectStore, screening: Screening) -> tuple[str, str, str] | None:
    if screening.baseline is None or screening.recent is None:
        return None
    images = await asyncio.to_thread(
        render, screening.baseline, screening.recent, screening.report.masks, screening.zones
    )
    keys = (
        new_object_key("watch/before", "png"),
        new_object_key("watch/after", "png"),
        new_object_key("watch/change", "png"),
    )
    for key, data in zip(keys, (images.before_png, images.after_png, images.change_png), strict=True):
        await store.put(key, data, "image/png")
    return keys


async def _save(
    session: AsyncSession,
    source: SceneSource,
    site_id: UUID,
    screening: Screening,
    keys: tuple[str, str, str] | None,
) -> ScanView:
    status = ScanStatus(screening.report.status.value)
    row = SiteScanRow(
        site_id=site_id,
        source=source.name,
        is_sample=source.is_sample,
        status=status,
        **_period_columns(screening.periods),
        baseline_scenes=screening.baseline_scenes,
        recent_scenes=screening.recent_scenes,
        valid_share=round(screening.report.valid_share, 4),
        score=screening.risk.score,
        level=screening.risk.level,
        signals=[_signal_json(s) for s in screening.risk.reasons],
        before_key=keys[0] if keys else None,
        after_key=keys[1] if keys else None,
        change_key=keys[2] if keys else None,
        mission_ids=[],
    )
    session.add(row)
    await session.flush()
    return _view(row)


async def _save_unavailable(
    session: AsyncSession, source: SceneSource, site_id: UUID, periods: Periods
) -> ScanView:
    row = SiteScanRow(
        site_id=site_id,
        source=source.name,
        is_sample=source.is_sample,
        status=ScanStatus.SOURCE_UNAVAILABLE,
        **_period_columns(periods),
        baseline_scenes=0,
        recent_scenes=0,
        valid_share=0.0,
        score=0,
        level=RiskLevel.UNKNOWN,
        signals=[],
        mission_ids=[],
    )
    session.add(row)
    await session.flush()
    return _view(row)


async def _row(session: AsyncSession, scan_id: UUID) -> SiteScanRow:
    row = await session.get(SiteScanRow, scan_id)
    if row is None:
        raise NotFound("not_found")
    return row


def _period_columns(periods: Periods) -> dict[str, date]:
    return {
        "baseline_start": periods.baseline_start,
        "baseline_end": periods.baseline_end,
        "recent_start": periods.recent_start,
        "recent_end": periods.recent_end,
    }


def _signal_json(signal: Signal) -> dict[str, Any]:
    return {
        "threat": signal.threat.value,
        "zone": signal.zone.value,
        "changed_pixels": signal.changed_pixels,
        "zone_pixels": signal.zone_pixels,
        "area_m2": signal.area_m2,
    }


def _view(row: SiteScanRow) -> ScanView:
    return ScanView(
        id=row.id,
        site_id=row.site_id,
        created_at=row.created_at,
        source=row.source,
        is_sample=row.is_sample,
        status=ScanStatus(row.status),
        periods=Periods(row.baseline_start, row.baseline_end, row.recent_start, row.recent_end),
        baseline_scenes=row.baseline_scenes,
        recent_scenes=row.recent_scenes,
        valid_share=row.valid_share,
        score=row.score,
        level=RiskLevel(row.level),
        signals=tuple(
            SignalView(
                Threat(s["threat"]), Zone(s["zone"]), s["changed_pixels"], s["zone_pixels"], s["area_m2"]
            )
            for s in row.signals
        ),
        before_key=row.before_key,
        after_key=row.after_key,
        change_key=row.change_key,
        acknowledged_at=row.acknowledged_at,
        ground_check_at=row.ground_check_at,
        mission_ids=tuple(UUID(m) for m in row.mission_ids),
    )
