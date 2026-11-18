from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from sadu.modules.watch.domain.change import Threat, Zone
from sadu.modules.watch.domain.risk import RiskLevel

TREND_STEP = 10
ALERT_LEVELS = frozenset({RiskLevel.MODERATE, RiskLevel.URGENT})


class Trend(StrEnum):
    NEW = "new"
    RISING = "rising"
    STEADY = "steady"
    FALLING = "falling"


class Confidence(StrEnum):
    FIRST_SIGHTING = "first_sighting"
    CONFIRMED = "confirmed"


@dataclass(frozen=True)
class Reading:
    score: int
    level: RiskLevel
    threats: frozenset[tuple[Threat, Zone]]


@dataclass(frozen=True)
class Warning:
    trend: Trend
    confidence: Confidence
    confirmed_threats: frozenset[tuple[Threat, Zone]]
    alert: bool


def warn(history: Iterable[Reading]) -> Warning | None:
    readings = list(history)
    if not readings:
        return None
    latest = readings[0]
    previous = readings[1] if len(readings) > 1 else None
    if previous is None:
        return Warning(Trend.NEW, Confidence.FIRST_SIGHTING, frozenset(), latest.level is RiskLevel.URGENT)
    confirmed = latest.threats & previous.threats
    delta = latest.score - previous.score
    trend = Trend.RISING if delta >= TREND_STEP else Trend.FALLING if delta <= -TREND_STEP else Trend.STEADY
    confidence = Confidence.CONFIRMED if confirmed else Confidence.FIRST_SIGHTING
    alert = latest.level is RiskLevel.URGENT or (latest.level in ALERT_LEVELS and bool(confirmed))
    return Warning(trend, confidence, confirmed, alert)
