from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.capture import api as capture
from sadu.modules.mapping import api as mapping
from sadu.modules.reports.domain.quality import QualityInputs, QualityReport, build_quality_report
from sadu.modules.verification import api as verification

SENT_BACK = (capture.ObservationStatus.NEEDS_RETAKE, capture.ObservationStatus.NEEDS_INPUT)
FINISHED = (*SENT_BACK, capture.ObservationStatus.DONE)


async def quality_report(session: AsyncSession) -> QualityReport:
    findings = await verification.finding_counts(session)
    maps = await mapping.approval_counts(session)
    photos = await capture.outcome_counts(session)
    return build_quality_report(
        QualityInputs(
            published_findings=findings.published,
            published_findings_with_evidence=findings.published_with_evidence,
            findings_pending_review=findings.pending_review,
            findings_rejected=findings.rejected,
            specialist_reviews=findings.expert_reviews,
            specialist_rejections=findings.expert_rejections,
            approved_maps=maps.approved,
            approved_maps_with_evidence=maps.approved_with_evidence,
            maps_corrected_by_specialist=maps.corrected_by_specialist,
            photos_finished=sum(photos.get(status, 0) for status in FINISHED),
            photos_sent_back=sum(photos.get(status, 0) for status in SENT_BACK),
        )
    )
