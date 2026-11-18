import pytest

from sadu.modules.agents.domain.planning import (
    DEFAULT_PLAN,
    GUIDE_ONLY_PLAN,
    STORY_ONLY_PLAN,
    ObservationContext,
    Step,
    accept_plan,
)

AT_SITE = ObservationContext(has_location=True, has_site=True, on_mission=False)
NO_CONSENT = ObservationContext(has_location=False, has_site=True, on_mission=False)


def test_valid_plan_is_kept() -> None:
    assert accept_plan(["identify", "guide"], AT_SITE) == (Step.IDENTIFY, Step.GUIDE)


@pytest.mark.parametrize(
    "proposed",
    [
        [],
        ["monitor", "identify", "verify", "guide"],
        ["identify", "monitor", "guide"],
        ["identify", "verify", "guide"],
        ["identify", "monitor", "verify"],
        ["identify", "guide", "guide"],
        ["identify", "delete_everything", "guide"],
    ],
)
def test_invalid_plans_fall_back_to_default(proposed: list[str]) -> None:
    assert accept_plan(proposed, AT_SITE) == DEFAULT_PLAN


def test_monitoring_without_location_consent_is_refused() -> None:
    assert accept_plan(["identify", "monitor", "verify", "guide"], NO_CONSENT) == STORY_ONLY_PLAN


def test_mission_photo_may_be_monitored_without_location() -> None:
    on_mission = ObservationContext(has_location=False, has_site=True, on_mission=True)
    assert accept_plan(list(DEFAULT_PLAN), on_mission) == DEFAULT_PLAN


@pytest.mark.parametrize("proposed", [["identify", "monitor", "verify", "guide"], ["identify", "guide"], []])
def test_site_without_facades_only_gets_its_story_and_stamp(proposed) -> None:
    district = ObservationContext(has_location=True, has_site=True, on_mission=False, has_facades=False)
    assert accept_plan(proposed, district) == GUIDE_ONLY_PLAN
