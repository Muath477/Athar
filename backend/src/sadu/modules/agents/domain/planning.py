"""Orchestrator plan invariants (docs/03-architecture.md §8, Orchestrator)."""

from dataclasses import dataclass
from enum import StrEnum


class Step(StrEnum):
    IDENTIFY = "identify"
    MONITOR = "monitor"
    VERIFY = "verify"
    GUIDE = "guide"


CANONICAL_ORDER = (Step.IDENTIFY, Step.MONITOR, Step.VERIFY, Step.GUIDE)
DEFAULT_PLAN = CANONICAL_ORDER
STORY_ONLY_PLAN = (Step.IDENTIFY, Step.GUIDE)


@dataclass(frozen=True)
class ObservationContext:
    has_location: bool
    has_site: bool
    on_mission: bool


def may_monitor(context: ObservationContext) -> bool:
    """Monitoring needs to know where the photo was taken and consent to use it for that."""
    return context.has_site and (context.has_location or context.on_mission)


def accept_plan(proposed: list[str], context: ObservationContext) -> tuple[Step, ...]:
    """Return the proposed plan if it is valid, otherwise the safe default for this context."""
    fallback = DEFAULT_PLAN if may_monitor(context) else STORY_ONLY_PLAN
    try:
        steps = tuple(Step(name) for name in proposed)
    except ValueError:
        return fallback
    if not _is_valid(steps, context):
        return fallback
    return steps


def _is_valid(steps: tuple[Step, ...], context: ObservationContext) -> bool:
    if len(set(steps)) != len(steps) or not steps or steps[-1] is not Step.GUIDE:
        return False
    if steps != tuple(step for step in CANONICAL_ORDER if step in steps):
        return False
    if (Step.MONITOR in steps) != (Step.VERIFY in steps):
        return False
    if Step.MONITOR in steps and (Step.IDENTIFY not in steps or not may_monitor(context)):
        return False
    return True
