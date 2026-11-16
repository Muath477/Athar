from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sadu.modules.missions.domain.priority import (
    MissionCandidate,
    MissionReason,
    coverage_gap_days,
    rank_candidates,
    select_missions,
)
from sadu.shared.vocabulary import Severity

NOW = datetime(2026, 11, 19, 12, tzinfo=UTC)


def gap(days: int) -> MissionCandidate:
    return MissionCandidate(f"gap-{days}", uuid4(), MissionReason.COVERAGE_GAP, days_since_last_photo=days)


def confirm(severity: Severity) -> MissionCandidate:
    return MissionCandidate(
        f"confirm-{severity}", uuid4(), MissionReason.CONFIRM_FINDING, uuid4(), severity
    )


def test_findings_outrank_gaps_and_urgent_comes_first() -> None:
    ranked = rank_candidates([gap(90), confirm(Severity.WATCH), gap(40), confirm(Severity.URGENT)])
    assert [c.candidate_id for c in ranked] == ["confirm-urgent", "confirm-watch", "gap-90", "gap-40"]


def test_selection_respects_open_slots_and_one_mission_per_facade() -> None:
    first, second = gap(60), gap(50)
    duplicate_facade = MissionCandidate("dup", first.facade_id, MissionReason.COVERAGE_GAP)
    chosen = select_missions([first, duplicate_facade, second], open_mission_facades={uuid4()})
    assert chosen == [first, second]


def test_no_slots_left() -> None:
    assert select_missions([gap(60)], {uuid4(), uuid4(), uuid4()}) == []


def test_coverage_gap_days() -> None:
    assert coverage_gap_days(NOW - timedelta(days=10), NOW) is None
    assert coverage_gap_days(NOW - timedelta(days=31), NOW) == 31
    assert coverage_gap_days(None, NOW) == 60
