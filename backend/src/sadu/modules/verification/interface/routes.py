from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from sadu.modules.admin.interface.auth import Expert, Staff
from sadu.modules.sites import api as sites
from sadu.modules.verification import api as verification
from sadu.shared.storage import ObjectStore
from sadu.shared.web import Session, State

router = APIRouter(tags=["findings"])


class Evidence(BaseModel):
    baseline_url: str | None
    photo_url: str | None
    diff_url: str | None


class FindingOut(BaseModel):
    id: str
    facade_id: str
    damage_type: str
    severity: str
    label: str
    status: str
    confirmations: int
    region_uv: list[float]
    pin_xyz: list[float]
    cause: str | None
    cause_label: str
    rationale_ar: str
    created_at: datetime
    evidence: Evidence | None = None


def finding_out(finding: verification.FindingView, store: ObjectStore | None = None) -> FindingOut:
    evidence = None
    if store is not None:
        evidence = Evidence(
            baseline_url=store.presigned_url(finding.baseline_key) if finding.baseline_key else None,
            photo_url=store.presigned_url(finding.photo_key) if finding.photo_key else None,
            diff_url=store.presigned_url(finding.diff_key) if finding.diff_key else None,
        )
    return FindingOut(
        id=str(finding.id),
        facade_id=str(finding.facade_id),
        damage_type=finding.damage_type,
        severity=finding.severity,
        label=finding.label,
        status=finding.status,
        confirmations=finding.confirmations,
        region_uv=finding.region_uv,
        pin_xyz=finding.pin_xyz,
        cause=finding.cause,
        cause_label="interpretation",
        rationale_ar=finding.rationale_ar,
        created_at=finding.created_at,
        evidence=evidence,
    )


@router.get("/sites/{site_id}/pins")
async def pins(
    site_id: UUID,
    _: Staff,
    session: Session,
    label: Annotated[str | None, Query(pattern="^(confirmed|likely)$")] = None,
    facade_id: UUID | None = None,
) -> list[FindingOut]:
    facade_ids = [f.id for f in await sites.list_facades(session, site_id) if facade_id in (None, f.id)]
    findings = await verification.published_for_facades(session, facade_ids)
    return [finding_out(f) for f in findings if label in (None, f.label)]


@router.get("/findings/{finding_id}")
async def get_finding(finding_id: UUID, _: Staff, session: Session, state: State) -> FindingOut:
    return finding_out(await verification.get_finding(session, finding_id), state.store)


@router.get("/review-queue")
async def review_queue(_: Expert, session: Session, state: State) -> list[FindingOut]:
    return [finding_out(f, state.store) for f in await verification.review_queue(session)]
