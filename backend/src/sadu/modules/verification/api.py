"""Public facade of the Verification module: the gate between detection and the dashboard."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.verification.application.claims import check_claims
from sadu.modules.verification.domain.claims import Chunk, Claim, ClaimLabel, ClaimVerdict, SourceKind
from sadu.modules.verification.domain.labels import Action, RegionSignals, Verdict, decide
from sadu.modules.verification.infrastructure.orm import FindingConfirmationRow, FindingRow, ReviewRow
from sadu.shared.errors import Conflict, NotFound
from sadu.shared.vocabulary import ConfidenceLabel, DamageType, ModelConfidence, Severity

__all__ = ["Chunk", "Claim", "ClaimLabel", "ClaimVerdict", "SourceKind", "check_claims"]

CORROBORATION_WINDOW = timedelta(days=30)
MIN_CORROBORATION_IOU = 0.2

type BoxUV = tuple[float, float, float, float]  # u0, v0, u1, v1


class FindingStatus(StrEnum):
    PUBLISHED = "published"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"


class ReviewDecision(StrEnum):
    CONFIRM = "confirm"
    CORRECT = "correct"
    REJECT = "reject"


@dataclass(frozen=True)
class RegionEvidence:
    """What Verification needs about one region; built by the agent from the inspection."""

    region_id: int
    region_uv: BoxUV
    pin_xyz: tuple[float, float, float]
    area_fraction: float
    pixel_lighting_flag: bool
    change_present: bool
    damage_type: DamageType
    visible_in_baseline: bool
    model_says_lighting: bool
    model_confidence: ModelConfidence
    model_severity: Severity
    likely_cause: str
    rationale_ar: str


@dataclass(frozen=True)
class EvidenceKeys:
    baseline_key: str
    photo_key: str
    diff_key: str


@dataclass(frozen=True)
class RecordedVerdict:
    region_id: int
    verdict: Verdict
    finding_id: UUID | None


@dataclass(frozen=True)
class FindingView:
    id: UUID
    facade_id: UUID
    observation_id: UUID
    damage_type: DamageType
    severity: Severity
    label: ConfidenceLabel
    status: FindingStatus
    confirmations: int
    region_uv: list[float]
    pin_xyz: list[float]
    cause: str | None
    rationale_ar: str
    baseline_key: str | None
    photo_key: str | None
    diff_key: str | None
    created_at: datetime


async def record_regions(
    session: AsyncSession,
    *,
    facade_id: UUID,
    observation_id: UUID,
    inspection_run_id: UUID,
    contributor: str,
    evidence: EvidenceKeys,
    regions: list[RegionEvidence],
) -> list[RecordedVerdict]:
    """Apply the label rule to each region and store what may be stored."""
    recorded = []
    for region in regions:
        existing = await _corroborated_finding(session, facade_id, region)
        contributors = await _contributors(session, existing.id) if existing else set()
        is_new_contributor = contributor not in contributors
        # Independent sources: distinct contributors who photographed this damage, this photo included.
        signals = _signals(region, len(contributors | {contributor}))
        verdict = decide(signals)
        finding_id = None
        if verdict.action in (Action.PUBLISH, Action.REVIEW):
            finding = existing or _new_finding(facade_id, observation_id, inspection_run_id, region, evidence)
            _apply_verdict(finding, verdict)
            finding.confirmations = signals.independent_confirmations
            if existing is None:
                session.add(finding)
                await session.flush()
            if is_new_contributor:
                session.add(
                    FindingConfirmationRow(
                        finding_id=finding.id, observation_id=observation_id, contributor_hash=contributor
                    )
                )
            finding_id = finding.id
        recorded.append(RecordedVerdict(region.region_id, verdict, finding_id))
    await session.flush()
    return recorded


async def record_unjudged_regions(
    session: AsyncSession,
    *,
    facade_id: UUID,
    observation_id: UUID,
    inspection_run_id: UUID,
    evidence: EvidenceKeys,
    regions: list[tuple[int, BoxUV, tuple[float, float, float]]],
) -> list[UUID]:
    """When the model is unavailable, changes go to an expert with their evidence, never to the map."""
    ids = []
    for region_id, region_uv, pin_xyz in regions:
        finding = FindingRow(
            facade_id=facade_id,
            observation_id=observation_id,
            inspection_run_id=inspection_run_id,
            region_id=region_id,
            damage_type=DamageType.OTHER,
            region_uv=list(region_uv),
            pin_xyz=list(pin_xyz),
            severity=Severity.WATCH,
            existence_label=ConfidenceLabel.UNKNOWN,
            status=FindingStatus.PENDING_REVIEW,
            reasons=["model_unavailable"],
            baseline_key=evidence.baseline_key,
            photo_key=evidence.photo_key,
            diff_key=evidence.diff_key,
        )
        session.add(finding)
        await session.flush()
        ids.append(finding.id)
    return ids


async def apply_review(
    session: AsyncSession,
    finding_id: UUID,
    *,
    reviewer_id: UUID,
    decision: ReviewDecision,
    reason: str,
    damage_type: DamageType | None = None,
    severity: Severity | None = None,
) -> FindingView:
    finding = await _finding_row(session, finding_id)
    if finding.status != FindingStatus.PENDING_REVIEW:
        raise Conflict("finding_not_in_review")
    changes: dict[str, Any] = {}
    if decision is ReviewDecision.REJECT:
        finding.status = FindingStatus.REJECTED
    else:
        if decision is ReviewDecision.CORRECT:
            if damage_type is not None:
                finding.damage_type = changes["damage_type"] = damage_type
            if severity is not None:
                finding.severity = changes["severity"] = severity
        finding.existence_label = ConfidenceLabel.CONFIRMED
        finding.status = FindingStatus.PUBLISHED
        finding.published_at = datetime.now(UTC)
    session.add(
        ReviewRow(
            finding_id=finding.id, reviewer_id=reviewer_id, decision=decision, changes=changes, reason=reason
        )
    )
    await session.flush()
    return _view(finding)


async def get_finding(session: AsyncSession, finding_id: UUID) -> FindingView:
    return _view(await _finding_row(session, finding_id))


async def published_for_facades(session: AsyncSession, facade_ids: list[UUID]) -> list[FindingView]:
    rows = await session.scalars(
        select(FindingRow)
        .where(FindingRow.facade_id.in_(facade_ids), FindingRow.status == FindingStatus.PUBLISHED)
        .order_by(FindingRow.created_at.desc())
    )
    return sorted((_view(r) for r in rows), key=lambda f: (-f.severity.rank, f.label != "confirmed"))


async def review_queue(session: AsyncSession) -> list[FindingView]:
    rows = await session.scalars(
        select(FindingRow)
        .where(FindingRow.status == FindingStatus.PENDING_REVIEW)
        .order_by(FindingRow.created_at)
    )
    return [_view(r) for r in rows]


async def needing_confirmation(session: AsyncSession, facade_ids: list[UUID]) -> list[FindingView]:
    rows = await session.scalars(
        select(FindingRow).where(
            FindingRow.facade_id.in_(facade_ids),
            FindingRow.status.in_([FindingStatus.PUBLISHED, FindingStatus.PENDING_REVIEW]),
            FindingRow.existence_label == ConfidenceLabel.LIKELY,
        )
    )
    return [_view(r) for r in rows]


def box_iou(a: BoxUV, b: BoxUV) -> float:
    width = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    intersection = width * height
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union if union > 0 else 0.0


async def _corroborated_finding(
    session: AsyncSession, facade_id: UUID, region: RegionEvidence
) -> FindingRow | None:
    since = datetime.now(UTC) - CORROBORATION_WINDOW
    candidates = await session.scalars(
        select(FindingRow).where(
            FindingRow.facade_id == facade_id,
            FindingRow.damage_type == region.damage_type,
            FindingRow.status != FindingStatus.REJECTED,
            FindingRow.created_at >= since,
        )
    )
    best = max(candidates, key=lambda f: box_iou(_box(f.region_uv), region.region_uv), default=None)
    if best is None or box_iou(_box(best.region_uv), region.region_uv) < MIN_CORROBORATION_IOU:
        return None
    return best


async def _contributors(session: AsyncSession, finding_id: UUID) -> set[str]:
    rows = await session.scalars(
        select(FindingConfirmationRow.contributor_hash).where(FindingConfirmationRow.finding_id == finding_id)
    )
    return set(rows)


def _signals(region: RegionEvidence, independent_confirmations: int) -> RegionSignals:
    return RegionSignals(
        quality_ok=True,
        alignment_ok=True,
        change_present=region.change_present,
        damage_type=region.damage_type,
        visible_in_baseline=region.visible_in_baseline,
        model_says_lighting=region.model_says_lighting,
        pixel_lighting_flag=region.pixel_lighting_flag,
        model_confidence=region.model_confidence,
        model_severity=region.model_severity,
        area_fraction=region.area_fraction,
        independent_confirmations=independent_confirmations,
    )


def _new_finding(
    facade_id: UUID, observation_id: UUID, run_id: UUID, region: RegionEvidence, evidence: EvidenceKeys
) -> FindingRow:
    return FindingRow(
        facade_id=facade_id,
        observation_id=observation_id,
        inspection_run_id=run_id,
        region_id=region.region_id,
        damage_type=region.damage_type,
        region_uv=list(region.region_uv),
        pin_xyz=list(region.pin_xyz),
        cause=region.likely_cause or None,
        rationale_ar=region.rationale_ar,
        baseline_key=evidence.baseline_key,
        photo_key=evidence.photo_key,
        diff_key=evidence.diff_key,
        severity=region.model_severity,
        existence_label=ConfidenceLabel.UNKNOWN,
        status=FindingStatus.PENDING_REVIEW,
    )


def _apply_verdict(finding: FindingRow, verdict: Verdict) -> None:
    if finding.status == FindingStatus.PUBLISHED and verdict.action is Action.REVIEW:
        return  # An already published finding is not pulled back for review by a second photo.
    finding.existence_label = verdict.label
    finding.severity = verdict.severity or finding.severity
    finding.reasons = list(verdict.reasons)
    if verdict.action is Action.PUBLISH:
        finding.status = FindingStatus.PUBLISHED
        finding.published_at = finding.published_at or datetime.now(UTC)
    else:
        finding.status = FindingStatus.PENDING_REVIEW


async def _finding_row(session: AsyncSession, finding_id: UUID) -> FindingRow:
    row = await session.get(FindingRow, finding_id)
    if row is None:
        raise NotFound("not_found")
    return row


def _box(values: list[float]) -> BoxUV:
    return (values[0], values[1], values[2], values[3])


def _view(row: FindingRow) -> FindingView:
    return FindingView(
        id=row.id,
        facade_id=row.facade_id,
        observation_id=row.observation_id,
        damage_type=DamageType(row.damage_type),
        severity=Severity(row.severity),
        label=ConfidenceLabel(row.existence_label),
        status=FindingStatus(row.status),
        confirmations=row.confirmations,
        region_uv=row.region_uv,
        pin_xyz=row.pin_xyz,
        cause=row.cause,
        rationale_ar=row.rationale_ar,
        baseline_key=row.baseline_key,
        photo_key=row.photo_key,
        diff_key=row.diff_key,
        created_at=row.created_at,
    )
