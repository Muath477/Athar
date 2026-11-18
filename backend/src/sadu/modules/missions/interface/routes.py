from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from sadu.modules.admin import api as admin
from sadu.modules.admin.interface.auth import Inspector
from sadu.modules.capture import api as capture
from sadu.modules.missions import api as missions
from sadu.modules.missions.domain.priority import MissionReason
from sadu.modules.sites import api as sites
from sadu.shared.web import Session, limit_public_reads, public

router = APIRouter(tags=["missions"])


class MissionOut(BaseModel):
    id: str
    site_id: str
    facade_id: str
    reason: str
    finding_id: str | None
    instruction_ar: str
    baseline_url: str
    expires_at: datetime


class NewMission(BaseModel):
    facade_id: UUID
    reason: MissionReason = MissionReason.COVERAGE_GAP
    finding_id: UUID | None = None


class FacadeCoverage(BaseModel):
    facade_id: str
    code: str
    name_ar: str
    days_since_last_photo: int | None
    open_mission_id: str | None


def mission_out(mission: missions.MissionView) -> MissionOut:
    return MissionOut(
        id=str(mission.id),
        site_id=str(mission.site_id),
        facade_id=str(mission.facade_id),
        reason=mission.reason,
        finding_id=str(mission.finding_id) if mission.finding_id else None,
        instruction_ar=mission.instruction_ar,
        baseline_url=f"/api/v1/facades/{mission.facade_id}/baseline",
        expires_at=mission.expires_at,
    )


@router.get("/missions/nearby", dependencies=[Depends(public), Depends(limit_public_reads)])
async def nearby_missions(
    session: Session,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
) -> list[MissionOut]:
    found: list[MissionOut] = []
    for site in await sites.find_sites_near(session, lat, lon, radius_m=300):
        found.extend(mission_out(m) for m in await missions.list_missions(session, site_id=site.id))
    return found


@router.get("/missions")
async def list_missions(_: Inspector, session: Session, site_id: UUID | None = None) -> list[MissionOut]:
    return [mission_out(m) for m in await missions.list_missions(session, site_id=site_id)]


@router.post("/missions", status_code=201)
async def create_mission(body: NewMission, user: Inspector, session: Session) -> MissionOut:
    mission = await missions.create_mission(session, body.facade_id, body.reason, body.finding_id)
    await admin.audit(
        session, actor_id=user.id, action="mission.create", target_type="mission", target_id=str(mission.id)
    )
    return mission_out(mission)


@router.get("/sites/{site_id}/coverage")
async def coverage(site_id: UUID, _: Inspector, session: Session) -> list[FacadeCoverage]:
    now = datetime.now(UTC)
    last_photos = await capture.last_usable_photo_per_facade(session, site_id)
    open_by_facade = {m.facade_id: m.id for m in await missions.list_missions(session, site_id=site_id)}
    result = []
    for facade in await sites.list_facades(session, site_id):
        last = last_photos.get(facade.id)
        result.append(
            FacadeCoverage(
                facade_id=str(facade.id),
                code=facade.code,
                name_ar=facade.name_ar,
                days_since_last_photo=(now - last).days if last else None,
                open_mission_id=str(open_by_facade[facade.id]) if facade.id in open_by_facade else None,
            )
        )
    return result
