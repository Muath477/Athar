"""Public facade of the Inspection module: compare one photo with one facade baseline."""

import asyncio
from dataclasses import asdict, dataclass, field
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.inspection.application.judge import build_request, judge_regions
from sadu.modules.inspection.domain.models import (
    AlignmentReport,
    ChangeRegion,
    QualityReport,
    RegionJudgment,
)
from sadu.modules.inspection.infrastructure import opencv_pipeline as cv
from sadu.modules.inspection.infrastructure.orm import InspectionRunRow
from sadu.shared.ports.llm import LLMPort, LLMRefused, LLMUnavailable, StructuredResult
from sadu.shared.storage import ObjectStore, new_object_key
from sadu.shared.vocabulary import RetakeReason

log = structlog.get_logger()


@dataclass(frozen=True)
class InspectionOutcome:
    run_id: UUID
    quality: QualityReport
    alignment: AlignmentReport | None
    regions: tuple[ChangeRegion, ...] = ()
    judgments: dict[int, RegionJudgment] = field(default_factory=dict)
    judge_failed: bool = False
    llm_result: StructuredResult | None = None
    baseline_key: str | None = None
    aligned_key: str | None = None
    diff_key: str | None = None

    @property
    def comparable(self) -> bool:
        return self.quality.ok and self.alignment is not None and self.alignment.ok

    @property
    def retake_reason(self) -> RetakeReason | None:
        if not self.quality.ok:
            return self.quality.retake_reason
        if not self.comparable:
            return RetakeReason.WRONG_ANGLE
        return None


@dataclass(frozen=True)
class _CvResult:
    quality: QualityReport
    alignment: AlignmentReport | None
    regions: tuple[ChangeRegion, ...]
    aligned_jpeg: bytes | None
    heatmap_jpeg: bytes | None


async def inspect(
    session: AsyncSession,
    store: ObjectStore,
    llm: LLMPort,
    *,
    observation_id: UUID,
    photo_jpeg: bytes,
    baseline_id: UUID,
    baseline_key: str,
) -> InspectionOutcome:
    baseline_jpeg = await store.get(baseline_key)
    result = await asyncio.to_thread(_run_cv, photo_jpeg, baseline_jpeg)

    aligned_key = diff_key = None
    if result.aligned_jpeg is not None and result.heatmap_jpeg is not None:
        aligned_key = new_object_key("aligned", "jpg")
        diff_key = new_object_key("diffs", "jpg")
        await store.put(aligned_key, result.aligned_jpeg, "image/jpeg")
        await store.put(diff_key, result.heatmap_jpeg, "image/jpeg")

    judgments: dict[int, RegionJudgment] = {}
    llm_result = None
    judge_failed = False
    if result.regions and result.aligned_jpeg and result.heatmap_jpeg:
        request = build_request(baseline_jpeg, result.aligned_jpeg, result.heatmap_jpeg, result.regions)
        try:
            judgments, llm_result = await judge_regions(llm, request, result.regions)
        except (LLMUnavailable, LLMRefused) as error:
            log.warning("damage_judgment_failed", observation_id=str(observation_id), error=str(error))
            judge_failed = True

    row = InspectionRunRow(
        observation_id=observation_id,
        baseline_id=baseline_id,
        quality=asdict(result.quality),
        alignment=asdict(result.alignment) if result.alignment else {},
        aligned_key=aligned_key,
        diff_key=diff_key,
        regions=[_region_json(r) for r in result.regions],
        judgment={str(k): _judgment_json(v) for k, v in judgments.items()} or None,
        model=llm_result.model if llm_result else None,
    )
    session.add(row)
    await session.flush()
    return InspectionOutcome(
        run_id=row.id,
        quality=result.quality,
        alignment=result.alignment,
        regions=result.regions,
        judgments=judgments,
        judge_failed=judge_failed,
        llm_result=llm_result,
        baseline_key=baseline_key,
        aligned_key=aligned_key,
        diff_key=diff_key,
    )


async def match_inliers(photo_jpeg: bytes, baseline_jpegs: list[bytes]) -> list[int]:
    """Feature-match inlier counts of the photo against each baseline, in the same order."""
    photo = cv.decode_image(photo_jpeg)
    return await asyncio.to_thread(
        lambda: [cv.count_matches(photo, cv.decode_image(b)) for b in baseline_jpegs]
    )


async def artifact_keys(session: AsyncSession, observation_ids: list[UUID]) -> list[str]:
    """Aligned photos and heat maps derived from these observations, for deletion with them."""
    rows = await session.execute(
        select(InspectionRunRow.aligned_key, InspectionRunRow.diff_key).where(
            InspectionRunRow.observation_id.in_(observation_ids)
        )
    )
    return [key for pair in rows.all() for key in pair if key]


def _run_cv(photo_jpeg: bytes, baseline_jpeg: bytes) -> _CvResult:
    photo, baseline = cv.decode_image(photo_jpeg), cv.decode_image(baseline_jpeg)
    quality = cv.assess_quality(photo)
    if not quality.ok:
        return _CvResult(quality, None, (), None, None)
    alignment = cv.align_to_baseline(photo, baseline)
    if not alignment.report.ok or alignment.warped is None or alignment.valid_mask is None:
        return _CvResult(quality, alignment.report, (), None, None)
    aligned_lab, baseline_lab = cv.normalize_lighting(alignment.warped, baseline, alignment.valid_mask)
    report, change_map = cv.find_changes(aligned_lab, baseline_lab, alignment.valid_mask)
    heatmap = cv.render_heatmap(baseline, change_map, report)
    return _CvResult(
        quality, alignment.report, report.regions, cv.encode_jpeg(alignment.warped), cv.encode_jpeg(heatmap)
    )


def _region_json(region: ChangeRegion) -> dict[str, object]:
    return {
        "region_id": region.region_id,
        "box": asdict(region.box),
        "area_fraction": region.area_fraction,
        "mean_change": region.mean_change,
        "lighting_flag": region.lighting_flag,
    }


def _judgment_json(judgment: RegionJudgment) -> dict[str, object]:
    return {
        key: str(value) if not isinstance(value, bool | int) else value
        for key, value in asdict(judgment).items()
    }
