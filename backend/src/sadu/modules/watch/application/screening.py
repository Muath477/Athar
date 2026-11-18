from dataclasses import dataclass
from datetime import date, timedelta

from sadu.modules.watch.application.ports import SceneSource, WatchArea
from sadu.modules.watch.domain.change import ChangeReport, ChangeRules, ScreeningStatus, detect_changes
from sadu.modules.watch.domain.geometry import Zones, zones
from sadu.modules.watch.domain.risk import Risk, assess
from sadu.modules.watch.domain.scene import Composite, median_composite

BUFFER_M = 150.0
RECENT_DAYS = 30
BASELINE_GAP_DAYS = 0
BASELINE_DAYS = 365
BASELINE_SCENES = 16
RECENT_SCENES = 6


@dataclass(frozen=True)
class Periods:
    baseline_start: date
    baseline_end: date
    recent_start: date
    recent_end: date

    @classmethod
    def ending(cls, today: date) -> "Periods":
        recent_start = today - timedelta(days=RECENT_DAYS)
        baseline_end = recent_start - timedelta(days=BASELINE_GAP_DAYS)
        return cls(baseline_end - timedelta(days=BASELINE_DAYS), baseline_end, recent_start, today)


@dataclass(frozen=True)
class Screening:
    periods: Periods
    report: ChangeReport
    risk: Risk
    zones: Zones
    baseline: Composite | None
    recent: Composite | None
    baseline_scenes: int
    recent_scenes: int


async def screen(source: SceneSource, area: WatchArea, today: date, rules: ChangeRules) -> Screening:
    periods = Periods.ending(today)
    site_zones = zones(area.boundary, area.center, area.window, BUFFER_M)
    baseline_scenes = await source.scenes(area, periods.baseline_start, periods.baseline_end, BASELINE_SCENES)
    recent_scenes = await source.scenes(area, periods.recent_start, periods.recent_end, RECENT_SCENES)
    counts = (len(baseline_scenes), len(recent_scenes))
    if not baseline_scenes or not recent_scenes:
        report = ChangeReport(ScreeningStatus.INSUFFICIENT_DATA, 0.0, ())
        return Screening(periods, report, assess(report), site_zones, None, None, *counts)

    baseline = median_composite(baseline_scenes)
    recent = median_composite(recent_scenes)
    report = detect_changes(baseline, recent, site_zones, area.window, rules)
    return Screening(periods, report, assess(report), site_zones, baseline, recent, *counts)
