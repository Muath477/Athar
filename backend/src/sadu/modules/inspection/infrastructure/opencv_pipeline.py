"""Quality gate, alignment, illumination normalization and difference map (docs §9, steps 2-5).

All images are BGR uint8 arrays. Functions are synchronous and CPU-bound; callers run them
in a worker thread.
"""

from dataclasses import dataclass

import cv2
import numpy as np
from cv2.typing import MatLike
from numpy.typing import NDArray
from skimage.metrics import structural_similarity

from sadu.modules.inspection.domain.models import (
    AlignmentReport,
    AlignmentThresholds,
    BoxPx,
    ChangeRegion,
    DifferenceReport,
    DifferenceThresholds,
    QualityReport,
    QualityThresholds,
)
from sadu.shared.vocabulary import RetakeReason

# OpenCV's stubs widen every array to MatLike; uint8 BGR is the convention, not a checked type.
type Image = MatLike
type Mask = MatLike

QUALITY_SIDE_PX = 1024
SIFT_FEATURES = 4000
LOWE_RATIO = 0.75
RANSAC_REPROJECTION_PX = 3.0
SSIM_WINDOW = 7
OPEN_KERNEL_PX = 5
CLOSE_KERNEL_PX = 9


def assess_quality(image: Image, limits: QualityThresholds = QualityThresholds()) -> QualityReport:
    gray = cv2.cvtColor(_fit_long_side(image, QUALITY_SIDE_PX), cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean_luminance = float(gray.mean())
    clipped_fraction = float(np.mean((gray < 5) | (gray > 250)))

    reason: RetakeReason | None = None
    if sharpness < limits.min_sharpness:
        reason = RetakeReason.BLURRY
    elif mean_luminance < limits.min_mean_luminance:
        reason = RetakeReason.TOO_DARK
    elif mean_luminance > limits.max_mean_luminance or clipped_fraction > limits.max_clipped_fraction:
        reason = RetakeReason.TOO_BRIGHT
    return QualityReport(sharpness, mean_luminance, clipped_fraction, reason)


@dataclass(frozen=True)
class Alignment:
    report: AlignmentReport
    warped: Image | None
    valid_mask: Mask | None


def count_matches(photo: Image, baseline: Image) -> int:
    """RANSAC inliers between two images; used by the Identifier to rank facades."""
    homography, inliers, _ = _estimate_homography(photo, baseline)
    return inliers if homography is not None else 0


def align_to_baseline(
    photo: Image, baseline: Image, limits: AlignmentThresholds = AlignmentThresholds()
) -> Alignment:
    homography, inliers, matches = _estimate_homography(photo, baseline)
    if homography is None or matches == 0:
        return Alignment(AlignmentReport(inliers, 0.0, 0.0, ok=False), None, None)

    height, width = baseline.shape[:2]
    warped = cv2.warpPerspective(photo, homography, (width, height))
    photo_area = np.full(photo.shape[:2], 255, dtype=np.uint8)
    valid_mask = cv2.warpPerspective(photo_area, homography, (width, height), flags=cv2.INTER_NEAREST)
    coverage = float(np.count_nonzero(valid_mask)) / valid_mask.size
    determinant = float(np.linalg.det(homography[:2, :2]))
    ratio = inliers / matches

    ok = (
        inliers >= limits.min_inliers
        and ratio >= limits.min_inlier_ratio
        and limits.min_determinant <= determinant <= limits.max_determinant
        and coverage >= limits.min_coverage
    )
    return Alignment(AlignmentReport(inliers, ratio, coverage, ok), warped, valid_mask)


def normalize_lighting(aligned: Image, baseline: Image, mask: Mask) -> tuple[Image, Image]:
    """CLAHE on both L channels, then match the aligned photo's L mean and spread to the baseline."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    aligned_lab = cv2.cvtColor(aligned, cv2.COLOR_BGR2LAB)
    baseline_lab = cv2.cvtColor(baseline, cv2.COLOR_BGR2LAB)
    aligned_lab[..., 0] = clahe.apply(aligned_lab[..., 0])
    baseline_lab[..., 0] = clahe.apply(baseline_lab[..., 0])

    inside = mask > 0
    source = aligned_lab[..., 0].astype(np.float32)
    target = baseline_lab[..., 0].astype(np.float32)
    source_std = float(source[inside].std()) or 1.0
    matched = (source - source[inside].mean()) * (float(target[inside].std()) / source_std)
    aligned_lab[..., 0] = np.clip(matched + target[inside].mean(), 0, 255).astype(np.uint8)
    return aligned_lab, baseline_lab


def find_changes(
    aligned_lab: Image,
    baseline_lab: Image,
    valid_mask: Mask,
    facade_mask: Mask | None = None,
    limits: DifferenceThresholds = DifferenceThresholds(),
) -> tuple[DifferenceReport, NDArray[np.float32]]:
    """Return change regions and the change map (0..1) used for the heat-map image."""
    area_mask = valid_mask if facade_mask is None else cv2.bitwise_and(valid_mask, facade_mask)
    change_map = _change_map(aligned_lab[..., 0], baseline_lab[..., 0]) * (area_mask > 0)

    thresholded: Mask = (change_map >= limits.change_threshold).astype(np.uint8) * 255
    opened = cv2.morphologyEx(thresholded, cv2.MORPH_OPEN, _kernel(OPEN_KERNEL_PX))
    binary = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, _kernel(CLOSE_KERNEL_PX))

    area_px = max(int(np.count_nonzero(area_mask)), 1)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    regions: list[ChangeRegion] = []
    for label in range(1, count):
        x, y, w, h, pixels = (int(v) for v in stats[label])
        if pixels / area_px < limits.min_region_fraction:
            continue
        component = labels == label
        regions.append(
            ChangeRegion(
                region_id=len(regions) + 1,
                box=BoxPx(x, y, w, h),
                area_fraction=pixels / area_px,
                mean_change=float(change_map[component].mean()),
                lighting_flag=_looks_like_lighting(aligned_lab, baseline_lab, component, limits),
            )
        )
    return DifferenceReport(tuple(regions)), change_map


def render_heatmap(baseline: Image, change_map: NDArray[np.float32], report: DifferenceReport) -> Image:
    """Baseline with the change map blended in red and numbered region boxes for the LLM."""
    heat = cv2.applyColorMap((change_map * 255).astype(np.uint8), cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(baseline, 0.6, heat, 0.4, 0)
    for region in report.regions:
        box = region.box
        cv2.rectangle(overlay, (box.x, box.y), (box.x + box.width, box.y + box.height), (255, 255, 255), 2)
        cv2.putText(
            overlay,
            str(region.region_id),
            (box.x + 4, box.y + 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )
    return overlay


def decode_image(data: bytes) -> Image:
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Image bytes could not be decoded")
    return image


def encode_jpeg(image: Image, quality: int = 85) -> bytes:
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("Image could not be encoded as JPEG")
    return buffer.tobytes()


def _estimate_homography(photo: Image, baseline: Image) -> tuple[MatLike | None, int, int]:
    sift = cv2.SIFT.create(nfeatures=SIFT_FEATURES)
    photo_keypoints, photo_descriptors = sift.detectAndCompute(_equalized_gray(photo), None)
    base_keypoints, base_descriptors = sift.detectAndCompute(_equalized_gray(baseline), None)
    if photo_descriptors is None or base_descriptors is None or len(base_keypoints) < 4:
        return None, 0, 0

    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(photo_descriptors, base_descriptors, k=2)
    good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < LOWE_RATIO * p[1].distance]
    if len(good) < 4:
        return None, 0, len(good)

    source = np.array([photo_keypoints[m.queryIdx].pt for m in good], dtype=np.float32).reshape(-1, 1, 2)
    target = np.array([base_keypoints[m.trainIdx].pt for m in good], dtype=np.float32).reshape(-1, 1, 2)
    homography, inlier_mask = cv2.findHomography(source, target, cv2.USAC_MAGSAC, RANSAC_REPROJECTION_PX)
    if homography is None:
        return None, 0, len(good)
    return homography, int(inlier_mask.sum()), len(good)


def _change_map(aligned_l: Image, baseline_l: Image) -> NDArray[np.float32]:
    """Half structural dissimilarity, half new-edge strength; sharp new edges (cracks, paint)
    score high while soft shadows mostly move brightness, not gradients."""
    _, ssim_map = structural_similarity(
        aligned_l, baseline_l, win_size=SSIM_WINDOW, full=True, data_range=255
    )
    dissimilarity: NDArray[np.float64] = np.clip(1.0 - ssim_map, 0.0, 1.0)
    gradient_delta = np.abs(_gradient_magnitude(aligned_l) - _gradient_magnitude(baseline_l))
    gradient_delta /= max(float(np.percentile(gradient_delta, 99.5)), 1e-6)
    return (0.5 * dissimilarity + 0.5 * np.clip(gradient_delta, 0.0, 1.0)).astype(np.float32)


def _looks_like_lighting(
    aligned_lab: Image, baseline_lab: Image, component: NDArray[np.bool_], limits: DifferenceThresholds
) -> bool:
    delta = aligned_lab.astype(np.float32) - baseline_lab.astype(np.float32)
    luminance_shift = float(np.abs(delta[..., 0][component]).mean())
    chroma_shift = float(np.abs(delta[..., 1:][component]).mean())
    structure = _structure_correlation(aligned_lab[..., 0], baseline_lab[..., 0], component)
    return (
        luminance_shift > limits.lighting_min_luminance_shift
        and chroma_shift < limits.lighting_max_chroma_shift
        and structure > limits.lighting_min_structure_correlation
    )


def _structure_correlation(a: Image, b: Image, component: NDArray[np.bool_]) -> float:
    grad_a = _gradient_magnitude(a)[component]
    grad_b = _gradient_magnitude(b)[component]
    if grad_a.std() == 0 or grad_b.std() == 0:
        return 0.0
    return float(np.corrcoef(grad_a, grad_b)[0, 1])


def _gradient_magnitude(channel: Image) -> NDArray[np.float32]:
    as_float = channel.astype(np.float32)
    dx = cv2.Sobel(as_float, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(as_float, cv2.CV_32F, 0, 1, ksize=3)
    return np.asarray(cv2.magnitude(dx, dy), dtype=np.float32)


def _equalized_gray(image: Image) -> Image:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return np.asarray(clahe.apply(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)), dtype=np.uint8)


def _fit_long_side(image: Image, side: int) -> Image:
    height, width = image.shape[:2]
    scale = side / max(height, width)
    if scale >= 1:
        return image
    return np.asarray(
        cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA),
        dtype=np.uint8,
    )


def _kernel(size: int) -> Mask:
    return np.asarray(cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)), dtype=np.uint8)
