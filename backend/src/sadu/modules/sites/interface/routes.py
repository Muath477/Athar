from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from sadu.modules.admin import api as admin
from sadu.modules.admin.interface.auth import SiteManager, Staff
from sadu.modules.sites import api as sites
from sadu.shared.web import Session, State, limit_public_reads, public

router = APIRouter(tags=["sites"])


class FacadeOut(BaseModel):
    id: str
    code: str
    name_ar: str
    name_en: str
    outward_azimuth_deg: float
    corners: list[list[float]]
    default_camera: dict[str, Any]


class LatLonOut(BaseModel):
    lat: float
    lon: float


class SiteOut(BaseModel):
    id: str
    slug: str
    name_ar: str
    name_en: str
    building_type: str
    model_url: str | None
    location: LatLonOut
    boundary: list[LatLonOut]
    facades: list[FacadeOut]
    field_photography_permitted: bool


class PermitIn(BaseModel):
    permitted: bool


async def site_out(session: Session, state: State, site: sites.SiteView) -> SiteOut:
    facades = await sites.list_facades(session, site.id)
    return SiteOut(
        id=str(site.id),
        slug=site.slug,
        name_ar=site.name_ar,
        name_en=site.name_en,
        building_type=site.building_type,
        model_url=state.store.presigned_url(site.model_key) if site.model_key else None,
        location=LatLonOut(lat=site.location.lat, lon=site.location.lon),
        boundary=[LatLonOut(lat=p.lat, lon=p.lon) for p in site.boundary],
        field_photography_permitted=site.field_photography_permitted,
        facades=[
            FacadeOut(
                id=str(f.id),
                code=f.code,
                name_ar=f.name_ar,
                name_en=f.name_en,
                outward_azimuth_deg=f.outward_azimuth_deg,
                corners=f.corners,
                default_camera=f.default_camera,
            )
            for f in facades
        ],
    )


@router.get("/sites/nearby", dependencies=[Depends(public), Depends(limit_public_reads)])
async def nearby_sites(
    session: Session,
    state: State,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
) -> list[SiteOut]:
    return [await site_out(session, state, s) for s in await sites.find_sites_near(session, lat, lon)]


@router.get("/sites")
async def list_sites(user: Staff, session: Session, state: State) -> list[SiteOut]:
    visible = [s for s in await sites.list_sites(session) if user.sees_site(s.id)]
    return [await site_out(session, state, s) for s in visible]


@router.get("/sites/{site_id}", dependencies=[Depends(public), Depends(limit_public_reads)])
async def get_site(site_id: UUID, session: Session, state: State) -> SiteOut:
    return await site_out(session, state, await sites.get_site(session, site_id))


@router.post("/sites/{site_id}/field-photography")
async def set_field_photography(
    site_id: UUID, body: PermitIn, user: SiteManager, session: Session, state: State, request: Request
) -> SiteOut:
    admin.ensure_sees_site(user, site_id)
    site = await sites.set_field_photography(session, site_id, body.permitted)
    await admin.audit(
        session,
        actor_id=user.id,
        action="site.field_photography",
        target_type="site",
        target_id=str(site_id),
        details={"permitted": body.permitted},
        request_id=getattr(request.state, "request_id", None),
    )
    return await site_out(session, state, site)


@router.get("/facades/{facade_id}/baseline", dependencies=[Depends(public), Depends(limit_public_reads)])
async def baseline_image(facade_id: UUID, session: Session, state: State) -> RedirectResponse:
    baseline = await sites.primary_baseline(session, facade_id)
    return RedirectResponse(state.store.presigned_url(baseline.object_key), status_code=307)
