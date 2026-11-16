"""The confidence-label rule from docs/03-architecture.md §9.

This is the only place that decides whether a detected change may reach the dashboard.
It is pure so every branch can be tested without images or a model.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from sadu.shared.vocabulary import (
    ConfidenceLabel,
    DamageType,
    ModelConfidence,
    RetakeReason,
    Severity,
)

CONFIRMATIONS_FOR_CONFIRMED = 2
BASAL_EROSION_URGENT_AREA = 0.05


class Action(StrEnum):
    PUBLISH = "publish"
    REVIEW = "review"
    RETAKE = "retake"
    DISCARD = "discard"


@dataclass(frozen=True)
class RegionSignals:
    """Everything the rule needs about one difference region."""

    quality_ok: bool
    alignment_ok: bool
    change_present: bool
    damage_type: DamageType
    visible_in_baseline: bool
    model_says_lighting: bool
    pixel_lighting_flag: bool
    model_confidence: ModelConfidence
    model_severity: Severity
    area_fraction: float
    independent_confirmations: int = 0
    expert_confirmed: bool = False


@dataclass(frozen=True)
class Verdict:
    label: ConfidenceLabel
    action: Action
    severity: Severity | None = None
    retake_reason: RetakeReason | None = None
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def reaches_dashboard(self) -> bool:
        return self.action is Action.PUBLISH


def decide(signals: RegionSignals) -> Verdict:
    if not signals.quality_ok or not signals.alignment_ok:
        return _retake(RetakeReason.WRONG_ANGLE, "photo_not_comparable")
    if not signals.change_present or signals.damage_type is DamageType.NONE:
        return _discard("no_change")
    if signals.visible_in_baseline:
        return _discard("pre_existing")
    if signals.model_says_lighting or signals.pixel_lighting_flag:
        return _retake(RetakeReason.LIGHTING, "possible_shadow_or_lighting")
    if signals.model_confidence is ModelConfidence.LOW:
        return _retake(RetakeReason.UNCLEAR_CHANGE, "low_model_confidence")

    severity = severity_with_floor(signals.damage_type, signals.model_severity, signals.area_fraction)
    if signals.expert_confirmed:
        return Verdict(ConfidenceLabel.CONFIRMED, Action.PUBLISH, severity, reasons=("expert_confirmed",))
    if signals.independent_confirmations >= CONFIRMATIONS_FOR_CONFIRMED:
        return Verdict(
            ConfidenceLabel.CONFIRMED, Action.PUBLISH, severity, reasons=("independent_confirmations",)
        )
    if severity is Severity.URGENT or signals.model_confidence is ModelConfidence.MEDIUM:
        return Verdict(ConfidenceLabel.LIKELY, Action.REVIEW, severity, reasons=("needs_expert",))
    return Verdict(ConfidenceLabel.LIKELY, Action.PUBLISH, severity, reasons=("single_source",))


def severity_with_floor(
    damage_type: DamageType, model_severity: Severity, area_fraction: float
) -> Severity:
    if damage_type is DamageType.PARTIAL_COLLAPSE:
        return Severity.URGENT
    if damage_type is DamageType.BASAL_EROSION and area_fraction >= BASAL_EROSION_URGENT_AREA:
        return Severity.URGENT
    if damage_type in (DamageType.MISSING_ELEMENT, DamageType.NEW_CONSTRUCTION):
        return model_severity.at_least(Severity.MODERATE)
    return model_severity


def _retake(reason: RetakeReason, why: str) -> Verdict:
    return Verdict(ConfidenceLabel.UNKNOWN, Action.RETAKE, retake_reason=reason, reasons=(why,))


def _discard(why: str) -> Verdict:
    return Verdict(ConfidenceLabel.UNKNOWN, Action.DISCARD, reasons=(why,))
