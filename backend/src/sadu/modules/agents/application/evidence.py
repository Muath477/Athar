"""Turn one inspection into what the Verifier needs, in facade coordinates."""

from sadu.modules.inspection.api import InspectionOutcome
from sadu.modules.inspection.domain.models import BoxPx
from sadu.modules.sites.api import BaselineView, FacadeView
from sadu.modules.verification.api import BoxUV, EvidenceKeys, RegionEvidence


def evidence_keys(outcome: InspectionOutcome, photo_key: str) -> EvidenceKeys | None:
    if outcome.baseline_key is None or outcome.diff_key is None:
        return None
    # The aligned photo is the evidence image: it overlays the baseline pixel for pixel.
    return EvidenceKeys(outcome.baseline_key, outcome.aligned_key or photo_key, outcome.diff_key)


def judged_regions(
    outcome: InspectionOutcome, baseline: BaselineView, facade: FacadeView
) -> list[RegionEvidence]:
    evidence = []
    for region in outcome.regions:
        judgment = outcome.judgments.get(region.region_id)
        if judgment is None:
            continue
        box = box_to_uv(region.box, baseline)
        evidence.append(
            RegionEvidence(
                region_id=region.region_id,
                region_uv=box,
                pin_xyz=facade.pin_position(_center(box)),
                area_fraction=region.area_fraction,
                pixel_lighting_flag=region.lighting_flag,
                change_present=judgment.change_present,
                damage_type=judgment.damage_type,
                visible_in_baseline=judgment.visible_in_baseline,
                model_says_lighting=judgment.lighting_or_shadow,
                model_confidence=judgment.confidence,
                model_severity=judgment.severity,
                likely_cause=judgment.likely_cause,
                rationale_ar=judgment.rationale_ar,
            )
        )
    return evidence


def unjudged_regions(
    outcome: InspectionOutcome, baseline: BaselineView, facade: FacadeView
) -> list[tuple[int, BoxUV, tuple[float, float, float]]]:
    regions = []
    for region in outcome.regions:
        box = box_to_uv(region.box, baseline)
        regions.append((region.region_id, box, facade.pin_position(_center(box))))
    return regions


def box_to_uv(box: BoxPx, baseline: BaselineView) -> BoxUV:
    """Pixel box (y down) to facade UV box (v up), as (u0, v0, u1, v1) with u0 < u1 and v0 < v1."""
    corners = [baseline.to_uv(x, y) for x in (box.x, box.x + box.width) for y in (box.y, box.y + box.height)]
    us, vs = [c[0] for c in corners], [c[1] for c in corners]
    return (min(us), min(vs), max(us), max(vs))


def _center(box: BoxUV) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
