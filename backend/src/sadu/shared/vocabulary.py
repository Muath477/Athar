from enum import StrEnum


class DamageType(StrEnum):
    CRACK = "crack"
    BASAL_EROSION = "basal_erosion"
    SURFACE_EROSION = "surface_erosion"
    MOISTURE = "moisture"
    PARTIAL_COLLAPSE = "partial_collapse"
    GRAFFITI = "graffiti"
    MISSING_ELEMENT = "missing_element"
    NEW_CONSTRUCTION = "new_construction"
    OTHER = "other"
    NONE = "none"


class Severity(StrEnum):
    WATCH = "watch"
    MODERATE = "moderate"
    URGENT = "urgent"

    @property
    def rank(self) -> int:
        return _SEVERITY_ORDER.index(self)

    def at_least(self, floor: "Severity") -> "Severity":
        return self if self.rank >= floor.rank else floor


_SEVERITY_ORDER = (Severity.WATCH, Severity.MODERATE, Severity.URGENT)


class ConfidenceLabel(StrEnum):
    CONFIRMED = "confirmed"
    LIKELY = "likely"
    ORAL_ACCOUNT = "oral_account"
    INTERPRETATION = "interpretation"
    UNKNOWN = "unknown"


class ModelConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RetakeReason(StrEnum):
    BLURRY = "blurry"
    TOO_DARK = "too_dark"
    TOO_BRIGHT = "too_bright"
    WRONG_ANGLE = "wrong_angle"
    LIGHTING = "lighting"
    UNCLEAR_CHANGE = "unclear_change"
