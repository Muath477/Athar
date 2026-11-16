from dataclasses import replace

import pytest

from sadu.modules.verification.domain.labels import Action, RegionSignals, decide, severity_with_floor
from sadu.shared.vocabulary import (
    ConfidenceLabel,
    DamageType,
    ModelConfidence,
    RetakeReason,
    Severity,
)

CLEAR_CRACK = RegionSignals(
    quality_ok=True,
    alignment_ok=True,
    change_present=True,
    damage_type=DamageType.CRACK,
    visible_in_baseline=False,
    model_says_lighting=False,
    pixel_lighting_flag=False,
    model_confidence=ModelConfidence.HIGH,
    model_severity=Severity.MODERATE,
    area_fraction=0.01,
)


def test_single_clear_change_is_published_as_likely() -> None:
    verdict = decide(CLEAR_CRACK)
    assert verdict.label is ConfidenceLabel.LIKELY
    assert verdict.action is Action.PUBLISH
    assert verdict.severity is Severity.MODERATE


@pytest.mark.parametrize(
    ("change", "expected_reason"),
    [
        ({"quality_ok": False}, RetakeReason.WRONG_ANGLE),
        ({"alignment_ok": False}, RetakeReason.WRONG_ANGLE),
        ({"model_says_lighting": True}, RetakeReason.LIGHTING),
        ({"pixel_lighting_flag": True}, RetakeReason.LIGHTING),
        ({"model_confidence": ModelConfidence.LOW}, RetakeReason.UNCLEAR_CHANGE),
    ],
)
def test_unusable_or_doubtful_evidence_asks_for_another_photo(
    change: dict[str, object], expected_reason: RetakeReason
) -> None:
    verdict = decide(replace(CLEAR_CRACK, **change))  # type: ignore[arg-type]
    assert verdict.label is ConfidenceLabel.UNKNOWN
    assert verdict.action is Action.RETAKE
    assert verdict.retake_reason is expected_reason
    assert not verdict.reaches_dashboard


@pytest.mark.parametrize(
    "change",
    [{"change_present": False}, {"damage_type": DamageType.NONE}, {"visible_in_baseline": True}],
)
def test_no_new_change_is_discarded(change: dict[str, object]) -> None:
    verdict = decide(replace(CLEAR_CRACK, **change))  # type: ignore[arg-type]
    assert verdict.action is Action.DISCARD
    assert not verdict.reaches_dashboard


def test_bad_photo_wins_over_everything_else() -> None:
    verdict = decide(replace(CLEAR_CRACK, quality_ok=False, expert_confirmed=True))
    assert verdict.action is Action.RETAKE


def test_two_independent_confirmations_make_it_confirmed() -> None:
    verdict = decide(replace(CLEAR_CRACK, independent_confirmations=2))
    assert verdict.label is ConfidenceLabel.CONFIRMED
    assert verdict.action is Action.PUBLISH


def test_one_confirmation_is_not_enough() -> None:
    assert decide(replace(CLEAR_CRACK, independent_confirmations=1)).label is ConfidenceLabel.LIKELY


def test_expert_confirmation_publishes_urgent_findings_directly() -> None:
    verdict = decide(replace(CLEAR_CRACK, model_severity=Severity.URGENT, expert_confirmed=True))
    assert verdict.label is ConfidenceLabel.CONFIRMED
    assert verdict.action is Action.PUBLISH


@pytest.mark.parametrize(
    "change",
    [{"model_severity": Severity.URGENT}, {"model_confidence": ModelConfidence.MEDIUM}],
)
def test_urgent_or_medium_confidence_single_source_goes_to_expert(change: dict[str, object]) -> None:
    verdict = decide(replace(CLEAR_CRACK, **change))  # type: ignore[arg-type]
    assert verdict.label is ConfidenceLabel.LIKELY
    assert verdict.action is Action.REVIEW


@pytest.mark.parametrize(
    ("damage_type", "model_severity", "area", "expected"),
    [
        (DamageType.PARTIAL_COLLAPSE, Severity.WATCH, 0.0, Severity.URGENT),
        (DamageType.BASAL_EROSION, Severity.WATCH, 0.05, Severity.URGENT),
        (DamageType.BASAL_EROSION, Severity.WATCH, 0.049, Severity.WATCH),
        (DamageType.MISSING_ELEMENT, Severity.WATCH, 0.0, Severity.MODERATE),
        (DamageType.NEW_CONSTRUCTION, Severity.URGENT, 0.0, Severity.URGENT),
        (DamageType.GRAFFITI, Severity.WATCH, 0.5, Severity.WATCH),
    ],
)
def test_severity_floor(
    damage_type: DamageType, model_severity: Severity, area: float, expected: Severity
) -> None:
    assert severity_with_floor(damage_type, model_severity, area) is expected


def test_collapse_from_one_visitor_is_reviewed_before_publishing() -> None:
    verdict = decide(replace(CLEAR_CRACK, damage_type=DamageType.PARTIAL_COLLAPSE))
    assert verdict.severity is Severity.URGENT
    assert verdict.action is Action.REVIEW
