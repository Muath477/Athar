from dataclasses import dataclass
from enum import StrEnum

from sadu.modules.watch.domain.change import ChangeReport, ScreeningStatus, Signal, Threat, Zone

THREAT_WEIGHT = {
    Threat.EARTHWORKS: 1.0,
    Threat.WATER: 1.0,
    Threat.CONSTRUCTION: 0.9,
    Threat.VEGETATION_LOSS: 0.6,
    Threat.SAND: 0.5,
}
ZONE_WEIGHT = {Zone.INSIDE: 1.0, Zone.RING: 0.5}
FULL_IMPACT_AREA_M2 = 2000.0
WORLD_HERITAGE_PRIORITY = 1.25


class RiskLevel(StrEnum):
    UNKNOWN = "unknown"
    STABLE = "stable"
    WATCH = "watch"
    MODERATE = "moderate"
    URGENT = "urgent"


LEVEL_FLOORS = ((60, RiskLevel.URGENT), (30, RiskLevel.MODERATE), (10, RiskLevel.WATCH))


@dataclass(frozen=True)
class Risk:
    score: int
    level: RiskLevel
    reasons: tuple[Signal, ...]


def assess(report: ChangeReport) -> Risk:
    if report.status is ScreeningStatus.INSUFFICIENT_DATA:
        return Risk(0, RiskLevel.UNKNOWN, ())
    weighted = [
        (THREAT_WEIGHT[s.threat] * ZONE_WEIGHT[s.zone] * min(1.0, s.area_m2 / FULL_IMPACT_AREA_M2), s)
        for s in report.signals
    ]
    score = min(100, round(100 * sum(weight for weight, _ in weighted)))
    reasons = tuple(s for _, s in sorted(weighted, key=lambda pair: -pair[0]))
    return Risk(score, level_for(score), reasons)


def level_for(score: int) -> RiskLevel:
    return next((level for floor, level in LEVEL_FLOORS if score >= floor), RiskLevel.STABLE)


def priority(risk: Risk, *, world_heritage: bool) -> float:
    return risk.score * (WORLD_HERITAGE_PRIORITY if world_heritage else 1.0)
