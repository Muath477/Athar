import sys
import time
from dataclasses import dataclass
from pathlib import Path

from sadu.modules.inspection.domain.models import AlignmentThresholds
from sadu.modules.inspection.infrastructure import opencv_pipeline as cv
from sadu.shared.vocabulary import RetakeReason

PACK_DIR = Path(__file__).resolve().parents[2] / "region-packs" / "demo"
BASELINES = ("north", "east", "south", "west")


@dataclass(frozen=True)
class Case:
    photo: str
    facade: str | None
    real_damage: bool
    lighting_only: bool = False


CASES = (
    Case("north-unchanged.jpg", "north", real_damage=False),
    Case("north-crack.jpg", "north", real_damage=True),
    Case("north-shadow.jpg", "north", real_damage=False, lighting_only=True),
    Case("not-a-facade.jpg", None, real_damage=False),
)


@dataclass(frozen=True)
class Outcome:
    case: Case
    identified: str | None
    retake_reason: RetakeReason | None
    damage_regions: int
    lighting_regions: int
    seconds: float

    @property
    def identified_correctly(self) -> bool:
        return self.identified == self.case.facade

    @property
    def flagged_damage(self) -> bool:
        return self.damage_regions > 0


def evaluate(case: Case, baselines: dict[str, cv.Image]) -> Outcome:
    started = time.perf_counter()
    photo = cv.decode_image((PACK_DIR / "test-photos" / case.photo).read_bytes())
    identified = _identify(photo, baselines)
    damage = lighting = 0
    retake: RetakeReason | None = None

    quality = cv.assess_quality(photo)
    if not quality.ok:
        retake = quality.retake_reason
    elif identified is None:
        retake = RetakeReason.WRONG_ANGLE
    else:
        baseline = baselines[identified]
        alignment = cv.align_to_baseline(photo, baseline)
        if not alignment.report.ok or alignment.warped is None or alignment.valid_mask is None:
            retake = RetakeReason.WRONG_ANGLE
        else:
            aligned_lab, baseline_lab = cv.normalize_lighting(
                alignment.warped, baseline, alignment.valid_mask
            )
            report, _ = cv.find_changes(aligned_lab, baseline_lab, alignment.valid_mask)
            lighting = sum(region.lighting_flag for region in report.regions)
            damage = len(report.regions) - lighting
    return Outcome(case, identified, retake, damage, lighting, time.perf_counter() - started)


def _identify(photo: cv.Image, baselines: dict[str, cv.Image]) -> str | None:
    counts = {name: cv.count_matches(photo, image) for name, image in baselines.items()}
    best = max(counts, key=lambda name: counts[name])
    return best if counts[best] >= AlignmentThresholds().min_inliers else None


def print_report(outcomes: list[Outcome]) -> None:
    print(f"{'photo':<22}{'facade':<10}{'retake':<14}{'damage':>7}{'light':>7}{'ms':>7}")
    for outcome in outcomes:
        print(
            f"{outcome.case.photo:<22}{outcome.identified or '-':<10}"
            f"{outcome.retake_reason or '-':<14}{outcome.damage_regions:>7}"
            f"{outcome.lighting_regions:>7}{outcome.seconds * 1000:>7.0f}"
        )

    damaged = [o for o in outcomes if o.case.real_damage]
    clean = [o for o in outcomes if not o.case.real_damage and o.case.facade is not None]
    lighting = [o for o in outcomes if o.case.lighting_only]
    off_target = [o for o in outcomes if o.case.facade is None]
    print()
    _metric("facade identification", sum(o.identified_correctly for o in outcomes), len(outcomes))
    _metric("damage recall", sum(o.flagged_damage for o in damaged), len(damaged))
    _metric("no false damage on unchanged facades", sum(not o.flagged_damage for o in clean), len(clean))
    _metric("shadows flagged as lighting", sum(o.lighting_regions > 0 for o in lighting), len(lighting))
    _metric(
        "off-target photos sent to retake",
        sum(o.retake_reason is not None for o in off_target),
        len(off_target),
    )
    slowest = max(o.seconds for o in outcomes)
    print(f"{'slowest photo':<40}{slowest * 1000:.0f} ms")


def _metric(name: str, hits: int, total: int) -> None:
    print(f"{name:<40}{hits}/{total}")


def main() -> int:
    baselines = {
        name: cv.decode_image((PACK_DIR / "baselines" / f"{name}.jpg").read_bytes()) for name in BASELINES
    }
    outcomes = [evaluate(case, baselines) for case in CASES]
    print_report(outcomes)
    failed = [o for o in outcomes if not _passes(o)]
    return 1 if failed else 0


def _passes(outcome: Outcome) -> bool:
    case = outcome.case
    if case.facade is None:
        return outcome.retake_reason is not None
    return (
        outcome.identified_correctly
        and outcome.retake_reason is None
        and outcome.flagged_damage == case.real_damage
        and (outcome.lighting_regions > 0 or not case.lighting_only)
    )


if __name__ == "__main__":
    sys.exit(main())
