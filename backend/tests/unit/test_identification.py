from uuid import uuid4

from sadu.modules.agents.domain.identification import (
    FacadeCandidate,
    IdentificationMethod,
    identify_facade,
)

NORTH, EAST, SOUTH = uuid4(), uuid4(), uuid4()


def test_clear_image_match_wins() -> None:
    result = identify_facade(
        [FacadeCandidate(NORTH, 120, None), FacadeCandidate(EAST, 30, None)], heading_accuracy_deg=None
    )
    assert (result.facade_id, result.method) == (NORTH, IdentificationMethod.IMAGE)


def test_close_image_scores_fall_back_to_trusted_heading() -> None:
    result = identify_facade(
        [FacadeCandidate(NORTH, 60, 0.95), FacadeCandidate(EAST, 50, 0.1)], heading_accuracy_deg=10
    )
    assert (result.facade_id, result.method) == (NORTH, IdentificationMethod.HEADING)


def test_inaccurate_heading_asks_the_visitor() -> None:
    result = identify_facade(
        [FacadeCandidate(NORTH, 20, 0.95), FacadeCandidate(EAST, 18, 0.1)], heading_accuracy_deg=45
    )
    assert result.ask_visitor
    assert result.facade_id is None
    assert set(result.options) == {NORTH, EAST}


def test_heading_without_margin_asks_the_visitor() -> None:
    result = identify_facade(
        [FacadeCandidate(NORTH, 10, 0.80), FacadeCandidate(EAST, 10, 0.70)], heading_accuracy_deg=5
    )
    assert result.ask_visitor


def test_visitor_options_are_capped_at_four() -> None:
    candidates = [FacadeCandidate(uuid4(), 5, None) for _ in range(6)]
    assert len(identify_facade(candidates, None).options) == 4


def test_no_candidates_means_no_identification() -> None:
    result = identify_facade([], None)
    assert result.method is IdentificationMethod.NONE
    assert not result.ask_visitor


def test_single_strong_candidate_is_accepted() -> None:
    assert identify_facade([FacadeCandidate(SOUTH, 40, None)], None).facade_id == SOUTH
