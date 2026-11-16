import cv2
import numpy as np
from cv2.typing import MatLike

from sadu.modules.inspection.domain.models import DifferenceReport
from sadu.modules.inspection.infrastructure.opencv_pipeline import (
    align_to_baseline,
    assess_quality,
    find_changes,
    normalize_lighting,
)
from sadu.shared.vocabulary import RetakeReason
from tests.synthetic import mud_wall, photograph, unrelated_scene, with_crack, with_soft_shadow

BASELINE = mud_wall()
CRACK_BOX = (420, 120, 455, 420)


def changes_between(baseline: MatLike, photo: MatLike) -> DifferenceReport:
    alignment = align_to_baseline(photo, baseline)
    assert alignment.report.ok, alignment.report
    assert alignment.warped is not None and alignment.valid_mask is not None
    aligned_lab, baseline_lab = normalize_lighting(alignment.warped, baseline, alignment.valid_mask)
    report, _ = find_changes(aligned_lab, baseline_lab, alignment.valid_mask)
    return report


def test_sharp_wall_passes_quality() -> None:
    assert assess_quality(BASELINE).ok


def test_blurred_photo_is_rejected() -> None:
    assert assess_quality(cv2.GaussianBlur(BASELINE, (0, 0), 6)).retake_reason is RetakeReason.BLURRY


def test_dark_photo_is_rejected() -> None:
    dark = (BASELINE * 0.15).astype(np.uint8)
    assert assess_quality(dark).retake_reason in {RetakeReason.TOO_DARK, RetakeReason.BLURRY}


def test_tilted_photo_aligns_to_baseline() -> None:
    report = align_to_baseline(photograph(BASELINE), BASELINE).report
    assert report.ok
    assert report.inliers >= 40


def test_unrelated_photo_does_not_align() -> None:
    assert not align_to_baseline(unrelated_scene(), BASELINE).report.ok


def test_same_wall_in_different_light_shows_no_change() -> None:
    assert not changes_between(BASELINE, photograph(BASELINE, brightness=0.8)).has_change


def test_new_crack_is_found_where_it_was_drawn() -> None:
    report = changes_between(BASELINE, photograph(with_crack(BASELINE)))
    assert report.has_change
    x0, y0, x1, y1 = CRACK_BOX
    centers = [r.box.center for r in report.regions]
    assert any(x0 - 20 <= cx <= x1 + 20 and y0 - 20 <= cy <= y1 + 20 for cx, cy in centers)
    assert not any(r.lighting_flag for r in report.regions if x0 - 20 <= r.box.center[0] <= x1 + 20)


def test_soft_shadow_is_not_reported_as_damage() -> None:
    report = changes_between(BASELINE, photograph(with_soft_shadow(BASELINE)))
    assert all(r.lighting_flag for r in report.regions)
