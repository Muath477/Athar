import pytest

from sadu.modules.models.domain.registry import ModelStatus, can_move


@pytest.mark.parametrize(
    ("current", "target", "allowed"),
    [
        (ModelStatus.CANDIDATE, ModelStatus.ACTIVE, True),
        (ModelStatus.CANDIDATE, ModelStatus.RETIRED, True),
        (ModelStatus.ACTIVE, ModelStatus.RETIRED, True),
        (ModelStatus.RETIRED, ModelStatus.ACTIVE, True),
        (ModelStatus.ACTIVE, ModelStatus.ACTIVE, False),
        (ModelStatus.RETIRED, ModelStatus.RETIRED, False),
        (ModelStatus.ACTIVE, ModelStatus.CANDIDATE, False),
    ],
)
def test_model_status_moves(current, target, allowed):
    assert can_move(current, target) is allowed
