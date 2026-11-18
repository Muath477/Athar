from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from sadu.shared.vocabulary import Severity

MAX_OPEN_MISSIONS_PER_SITE = 3
COVERAGE_MAX_AGE = timedelta(days=30)


class MissionReason(StrEnum):
    CONFIRM_FINDING = "confirm_finding"
    COVERAGE_GAP = "coverage_gap"
    SATELLITE_ALERT = "satellite_alert"


@dataclass(frozen=True)
class MissionCandidate:
    candidate_id: str
    facade_id: UUID
    reason: MissionReason
    finding_id: UUID | None = None
    finding_severity: Severity | None = None
    days_since_last_photo: int | None = None


def coverage_gap_days(last_photo_at: datetime | None, now: datetime) -> int | None:
    if last_photo_at is None:
        return COVERAGE_MAX_AGE.days * 2
    age = now - last_photo_at
    return age.days if age > COVERAGE_MAX_AGE else None


def rank_candidates(candidates: list[MissionCandidate]) -> list[MissionCandidate]:
    return sorted(candidates, key=_priority_key)


def select_missions(
    candidates: list[MissionCandidate], open_mission_facades: set[UUID]
) -> list[MissionCandidate]:
    free_slots = MAX_OPEN_MISSIONS_PER_SITE - len(open_mission_facades)
    chosen: list[MissionCandidate] = []
    taken = set(open_mission_facades)
    for candidate in candidates:
        if len(chosen) >= free_slots:
            break
        if candidate.facade_id in taken:
            continue
        chosen.append(candidate)
        taken.add(candidate.facade_id)
    return chosen


def _priority_key(candidate: MissionCandidate) -> tuple[int, int, int]:
    if candidate.reason is MissionReason.CONFIRM_FINDING:
        severity_rank = candidate.finding_severity.rank if candidate.finding_severity else 0
        return (0, -severity_rank, 0)
    return (1, 0, -(candidate.days_since_last_photo or 0))
