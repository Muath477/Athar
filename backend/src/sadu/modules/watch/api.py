import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

import structlog
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
from sadu.shared.web import UnitOfWork

__all__ = [
    "THREAT_COLORS",
    "GroundCheck",
    "RiskLevel",
    "ScanQueue",
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
    "watch_area",
]

log = structlog.get_logger()

WORLD_HERITAGE_TYPE = "world_heritage"
GROUND_CHECK_FACADES = 3
RETRY_FAILED_AFTER = timedelta(hours=6)
RECENT_SCANS = 10
CONCURRENT_SCANS = 2
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
    failed_attempt: ScanView | None
    priority: float
    scanning: bool


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
    now = now or datetime.now(UTC)
    due = []
    for site in await sites.list_sites(session):
        history = await site_scans(session, site.id, limit=RECENT_SCANS)
        latest_ok = _latest_ok(history)
        fresh = latest_ok is not None and latest_ok.created_at > now - interval
        retried_lately = bool(history) and history[0].created_at > now - RETRY_FAILED_AFTER
        if not fresh and not retried_lately:
            due.append(site.id)
    return due


class ScanQueue:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        store: ObjectStore,
        source: SceneSource,
        concurrency: int = CONCURRENT_SCANS,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._store = store
        self._source = source
        self._slots = asyncio.Semaphore(concurrency)
        self._running: dict[UUID, asyncio.Task[ScanView | None]] = {}

    @property
    def source(self) -> SceneSource:
        return self._source

    def running(self, site_id: UUID) -> bool:
        return site_id in self._running

    def start(self, site_id: UUID) -> bool:
        if site_id in self._running:
            return False
        task = asyncio.create_task(self._scan(site_id))
        self._running[site_id] = task
        task.add_done_callback(lambda _: self._running.pop(site_id, None))
        return True

    async def join(self) -> None:
        await asyncio.gather(*self._running.values(), return_exceptions=True)

    async def _scan(self, site_id: UUID) -> ScanView | None:
        async with self._slots:
            try:
                scan = await scan_site(self._unit_of_work, self._store, self._source, site_id)
            except Exception:
                log.exception("site_scan_failed", site_id=str(site_id))
                return None
        log.info("site_scanned", site_id=str(site_id), status=scan.status, level=scan.level)
        return scan


async def watch_area(session: AsyncSession, site_id: UUID) -> WatchArea:
    site = await sites.get_site(session, site_id)
    center = LatLon(site.location.lat, site.location.lon)
    boundary = [LatLon(p.lat, p.lon) for p in site.boundary]
    return WatchArea(site.id, site.slug, center, boundary, window_for(boundary, center, BUFFER_M))


async def scan_site(
    unit_of_work: UnitOfWork,
    store: ObjectStore,
    source: SceneSource,
    site_id: UUID,
    *,
    today: date | None = None,
    rules: ChangeRules | None = None,
) -> ScanView:
    async with unit_of_work() as session:
        area = await watch_area(session, site_id)
    today = today or datetime.now(UTC).date()
    try:
        screening = await screen(source, area, today, rules or ChangeRules())
    except SceneSourceUnavailable:
        async with unit_of_work() as session:
            return await _save_unavailable(session, source, site_id, Periods.ending(today))
    keys = await _store_evidence(store, screening)
    async with unit_of_work() as session:
        return await _save(session, source, site_id, screening, keys)


async def site_scans(session: AsyncSession, site_id: UUID, limit: int = 20) -> list[ScanView]:
    rows = await session.scalars(
        select(SiteScanRow)
        .where(SiteScanRow.site_id == site_id)
        .order_by(SiteScanRow.created_at.desc())
        .limit(limit)
    )
    return [_view(row) for row in rows]


async def rank_sites(session: AsyncSession, queue: ScanQueue | None = None) -> list[SiteRisk]:
    ranked = []
    for site in await sites.list_sites(session):
        history = await site_scans(session, site.id, limit=RECENT_SCANS)
        latest = _latest_ok(history)
        failed = history[0] if history and history[0] is not latest else None
        score = 0.0
        if latest is not None:
            score = priority_of(latest, world_heritage=site.building_type == WORLD_HERITAGE_TYPE)
        facades = len(await sites.list_facades(session, site.id))
        scanning = queue is not None and queue.running(site.id)
        ranked.append(SiteRisk(site, facades, latest, failed, score, scanning))
    return sorted(
        ranked, key=lambda r: (-_level_rank(r.latest), -r.priority, r.latest is None, r.site.name_ar)
    )


def _latest_ok(history: list[ScanView]) -> ScanView | None:
    return next((scan for scan in history if scan.status is ScanStatus.OK), None)


def _level_rank(scan: ScanView | None) -> int:
    return LEVEL_RANK[scan.level] if scan is not None else 0


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
    scan = _view(row)
    if scan.status is not ScanStatus.OK or not scan.signals:
        raise Conflict("scan_has_no_alert")
    latest = _latest_ok(await site_scans(session, row.site_id, limit=RECENT_SCANS))
    if latest is None or latest.id != scan.id:
        raise Conflict("scan_superseded")
    opened = []
    covered = 0
    site = await sites.get_site(session, row.site_id)
    facades = await sites.list_facades(session, row.site_id) if site.field_photography_permitted else []
    for facade in facades[:GROUND_CHECK_FACADES]:
        try:
            opened.append(
                await missions.create_mission(session, facade.id, missions.MissionReason.SATELLITE_ALERT)
            )
            covered += 1
        except Conflict:
            covered += 1
        except NotFound:
            continue
    row.ground_check_at = datetime.now(UTC)
    row.mission_ids = [*row.mission_ids, *(str(m.id) for m in opened)]
    await session.flush()
    return GroundCheck(_view(row), tuple(opened), inspector_visit=covered == 0)


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
