import argparse
import asyncio
import csv
import json
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from sadu.modules.watch.application.ports import SceneSource, SceneSourceUnavailable, WatchArea
from sadu.modules.watch.application.screening import BUFFER_M, Screening, screen
from sadu.modules.watch.domain.change import ChangeRules
from sadu.modules.watch.domain.geometry import LatLon, window_for
from sadu.modules.watch.domain.risk import RiskLevel
from sadu.modules.watch.infrastructure.earth_search import EarthSearchSceneSource
from sadu.modules.watch.infrastructure.evidence import render
from sadu.modules.watch.infrastructure.sample_source import SampleSceneSource
from sadu.shared.config import get_settings

ALERT_LEVELS = {RiskLevel.WATCH, RiskLevel.MODERATE, RiskLevel.URGENT}
ALERT_VALUES = {level.value for level in ALERT_LEVELS}
FIELDS = [
    "slug",
    "name_en",
    "recent_start",
    "recent_end",
    "status",
    "valid_share",
    "score",
    "level",
    "signals",
    "evidence",
    "truth",
    "notes",
]
TARGET_PRECISION = 0.6
TARGET_REAL_CHANGES = 3


@dataclass(frozen=True)
class PackSite:
    slug: str
    name_en: str
    area: WatchArea


def load_sites(pack_dir: Path, slugs: set[str]) -> list[PackSite]:
    pack: dict[str, Any] = json.loads((pack_dir / "pack.json").read_text(encoding="utf-8"))
    sites = []
    for site in pack["sites"]:
        if slugs and site["slug"] not in slugs:
            continue
        centre = LatLon(site["location"][1], site["location"][0])
        boundary = [LatLon(lat, lon) for lon, lat in site["boundary"]]
        area = WatchArea(uuid4(), site["slug"], centre, boundary, window_for(boundary, centre, BUFFER_M))
        sites.append(PackSite(site["slug"], site["name_en"], area))
    return sites


def run_dates(start: date, end: date, step_days: int) -> list[date]:
    dates = [start]
    current = start + timedelta(days=step_days)
    while current <= end:
        dates.append(current)
        current += timedelta(days=step_days)
    if dates[-1] != end:
        dates.append(end)
    return dates


def describe(screening: Screening) -> str:
    return "; ".join(f"{s.threat.value}/{s.zone.value}/{round(s.area_m2)}m2" for s in screening.risk.reasons)


def save_evidence(screening: Screening, folder: Path) -> str:
    if screening.baseline is None or screening.recent is None:
        return ""
    folder.mkdir(parents=True, exist_ok=True)
    images = render(screening.baseline, screening.recent, screening.report.masks, screening.zones)
    for name, data in (
        ("before", images.before_png),
        ("after", images.after_png),
        ("change", images.change_png),
    ):
        (folder / f"{name}.png").write_bytes(data)
    return str(folder)


async def backtest(source: SceneSource, sites: list[PackSite], dates: list[date], out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    table = out / "alerts.csv"
    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for site in sites:
            for today in dates:
                row = {"slug": site.slug, "name_en": site.name_en, "recent_end": today.isoformat()}
                try:
                    screening = await screen(source, site.area, today, ChangeRules())
                except SceneSourceUnavailable as error:
                    writer.writerow({**row, "status": "source_unavailable", "notes": str(error)})
                    continue
                alert = screening.risk.level in ALERT_LEVELS
                writer.writerow(
                    {
                        **row,
                        "recent_start": screening.periods.recent_start.isoformat(),
                        "status": screening.report.status.value,
                        "valid_share": round(screening.report.valid_share, 3),
                        "score": screening.risk.score,
                        "level": screening.risk.level.value,
                        "signals": describe(screening),
                        "evidence": save_evidence(screening, out / site.slug / today.isoformat())
                        if alert
                        else "",
                    }
                )
                handle.flush()
                print(f"{site.slug} {today} {screening.risk.level.value} {describe(screening)}")
    return table


@dataclass(frozen=True)
class Precision:
    alerts: int
    reviewed: int
    confirmed: int

    @property
    def precision(self) -> float:
        return self.confirmed / self.reviewed if self.reviewed else 0.0

    @property
    def passed(self) -> bool:
        return self.precision >= TARGET_PRECISION and self.confirmed >= TARGET_REAL_CHANGES


def score(table: Path) -> Precision:
    with table.open(encoding="utf-8") as handle:
        alerts = [row for row in csv.DictReader(handle) if row["level"] in ALERT_VALUES]
    reviewed = [row for row in alerts if row["truth"].strip().lower() in {"yes", "no"}]
    confirmed = sum(row["truth"].strip().lower() == "yes" for row in reviewed)
    return Precision(len(alerts), len(reviewed), confirmed)


def build_source(kind: str) -> SceneSource:
    settings = get_settings()
    if kind == "sample":
        return SampleSceneSource(settings.watch_sample_events_path)
    return EarthSearchSceneSource(settings.sadu_scene_search_url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay satellite screening over past dates for review")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--pack", default="riyadh")
    run.add_argument("--sites", default="", help="comma-separated slugs, empty for all")
    run.add_argument("--start", type=date.fromisoformat, required=True)
    run.add_argument("--end", type=date.fromisoformat, required=True)
    run.add_argument("--step-days", type=int, default=60)
    run.add_argument("--source", choices=["earth_search", "sample"], default="earth_search")
    run.add_argument("--out", type=Path, default=Path("watch-backtest"))
    review = commands.add_parser("score")
    review.add_argument("table", type=Path)
    args = parser.parse_args()

    if args.command == "score":
        result = score(args.table)
        print(
            f"alerts {result.alerts}, reviewed {result.reviewed}, confirmed {result.confirmed}, "
            f"precision {result.precision:.2f} (target {TARGET_PRECISION:.2f} "
            f"and at least {TARGET_REAL_CHANGES} real changes)"
        )
        sys.exit(0 if result.passed else 1)

    pack_dir = Path(get_settings().sadu_region_packs_dir) / args.pack
    slugs = {s.strip() for s in args.sites.split(",") if s.strip()}
    sites = load_sites(pack_dir, slugs)
    if not sites:
        sys.exit(f"No sites matched {sorted(slugs)} in {pack_dir}")
    table = asyncio.run(
        backtest(build_source(args.source), sites, run_dates(args.start, args.end, args.step_days), args.out)
    )
    print(f"Wrote {table}. Fill the truth column with yes or no from historical imagery, then run score.")


if __name__ == "__main__":
    main()
