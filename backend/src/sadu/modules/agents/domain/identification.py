"""Identifier decision rule (docs/03-architecture.md §8, Identifier)."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

MIN_INLIERS = 40
INLIER_MARGIN = 1.5
MAX_USABLE_HEADING_ERROR_DEG = 30.0
MAX_TRUSTED_HEADING_ERROR_DEG = 20.0
# cos(45°): the best facade must face the camera at least 45° better than the runner-up.
MIN_HEADING_SCORE_MARGIN = 0.29


class IdentificationMethod(StrEnum):
    IMAGE = "image"
    HEADING = "heading"
    VISITOR = "visitor"
    NONE = "none"


@dataclass(frozen=True)
class FacadeCandidate:
    facade_id: UUID
    inliers: int
    heading_score: float | None


@dataclass(frozen=True)
class Identification:
    facade_id: UUID | None
    method: IdentificationMethod
    ask_visitor: bool
    options: tuple[UUID, ...] = ()


def identify_facade(candidates: list[FacadeCandidate], heading_accuracy_deg: float | None) -> Identification:
    if not candidates:
        return Identification(None, IdentificationMethod.NONE, ask_visitor=False)

    by_inliers = sorted(candidates, key=lambda c: c.inliers, reverse=True)
    best = by_inliers[0]
    runner_up_inliers = by_inliers[1].inliers if len(by_inliers) > 1 else 0
    if best.inliers >= MIN_INLIERS and best.inliers >= INLIER_MARGIN * runner_up_inliers:
        return Identification(best.facade_id, IdentificationMethod.IMAGE, ask_visitor=False)

    by_heading = _trusted_heading_ranking(candidates, heading_accuracy_deg)
    if by_heading:
        return Identification(by_heading[0].facade_id, IdentificationMethod.HEADING, ask_visitor=False)

    options = tuple(c.facade_id for c in _visitor_options(candidates, heading_accuracy_deg))
    return Identification(None, IdentificationMethod.VISITOR, ask_visitor=True, options=options)


def _trusted_heading_ranking(
    candidates: list[FacadeCandidate], heading_accuracy_deg: float | None
) -> list[FacadeCandidate]:
    """Facades ranked by heading, or [] when the heading cannot decide on its own."""
    if heading_accuracy_deg is None or heading_accuracy_deg > MAX_TRUSTED_HEADING_ERROR_DEG:
        return []
    scored = sorted(
        (c for c in candidates if c.heading_score is not None),
        key=lambda c: c.heading_score or 0.0,
        reverse=True,
    )
    if not scored:
        return []
    best_score = scored[0].heading_score or 0.0
    runner_up_score = (scored[1].heading_score or 0.0) if len(scored) > 1 else -1.0
    if best_score - runner_up_score < MIN_HEADING_SCORE_MARGIN:
        return []
    return scored


def _visitor_options(
    candidates: list[FacadeCandidate], heading_accuracy_deg: float | None
) -> list[FacadeCandidate]:
    heading_usable = heading_accuracy_deg is not None and heading_accuracy_deg <= MAX_USABLE_HEADING_ERROR_DEG

    def rank(candidate: FacadeCandidate) -> tuple[float, int]:
        heading = candidate.heading_score if heading_usable and candidate.heading_score else 0.0
        return (heading, candidate.inliers)

    return sorted(candidates, key=rank, reverse=True)[:4]
