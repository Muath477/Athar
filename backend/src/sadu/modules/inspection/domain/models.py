from dataclasses import dataclass, field

from sadu.shared.vocabulary import DamageType, ModelConfidence, RetakeReason, Severity


@dataclass(frozen=True)
class QualityThresholds:
    min_sharpness: float = 80.0
    min_mean_luminance: float = 40.0
    max_mean_luminance: float = 215.0
    max_clipped_fraction: float = 0.15


@dataclass(frozen=True)
class QualityReport:
    sharpness: float
    mean_luminance: float
    clipped_fraction: float
    retake_reason: RetakeReason | None

    @property
    def ok(self) -> bool:
        return self.retake_reason is None


@dataclass(frozen=True)
class AlignmentThresholds:
    min_inliers: int = 40
    min_inlier_ratio: float = 0.25
    min_determinant: float = 0.2
    max_determinant: float = 5.0
    min_coverage: float = 0.6


@dataclass(frozen=True)
class AlignmentReport:
    inliers: int
    inlier_ratio: float
    coverage: float
    ok: bool


@dataclass(frozen=True)
class DifferenceThresholds:
    change_threshold: float = 0.35
    min_region_fraction: float = 0.001
    lighting_min_luminance_shift: float = 25.0
    lighting_max_chroma_shift: float = 10.0
    lighting_min_structure_correlation: float = 0.75


@dataclass(frozen=True)
class BoxPx:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)


@dataclass(frozen=True)
class ChangeRegion:
    region_id: int
    box: BoxPx
    area_fraction: float
    mean_change: float
    lighting_flag: bool


@dataclass(frozen=True)
class DifferenceReport:
    regions: tuple[ChangeRegion, ...] = field(default_factory=tuple)

    @property
    def has_change(self) -> bool:
        return bool(self.regions)


@dataclass(frozen=True)
class RegionJudgment:
    region_id: int
    change_present: bool
    damage_type: DamageType
    visible_in_baseline: bool
    lighting_or_shadow: bool
    severity: Severity
    confidence: ModelConfidence
    likely_cause: str
    rationale_ar: str
