from enum import StrEnum


class ModelStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    RETIRED = "retired"


ALLOWED_MOVES: dict[ModelStatus, frozenset[ModelStatus]] = {
    ModelStatus.CANDIDATE: frozenset({ModelStatus.ACTIVE, ModelStatus.RETIRED}),
    ModelStatus.ACTIVE: frozenset({ModelStatus.RETIRED}),
    ModelStatus.RETIRED: frozenset({ModelStatus.ACTIVE}),
}


def can_move(current: ModelStatus, target: ModelStatus) -> bool:
    return target in ALLOWED_MOVES[current]
