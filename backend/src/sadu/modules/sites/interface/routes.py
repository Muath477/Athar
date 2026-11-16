from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from sadu.modules.admin.interface.auth import Inspector
from sadu.modules.sites import api as sites
from sadu.shared.web import Session, State, public

router = APIRouter(tags=["sites"])


class FacadeOut(BaseModel):
    id: str
    code: str
    name_ar: str
    name_en: str
    outward_azimuth_deg: float
    corners: list[list[float]]
    default_camera: dict[str, Any]


class SiteOut(BaseModel):
    id: str
    slug: str
    name_ar: str
    name_en: str
    building_type: str
    model_url: str | None
    facades: list[FacadeOut]


async def site_out(session: Session, state: State, site: sites.SiteView) -> SiteOut:
    facades = await sites.list_facades(session, site.id)
    return SiteOut(
        id=str(site.id),
        slug=site.slug,
        name_ar=site.name_ar,
        name_en=site.name_en,
        building_type=site.building_type,
        model_url=state.store.presigned_url(site.model_key) if site.model_key else None,
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


@router.get("/sites/nearby", dependencies=[Depends(public)])
async def nearby_sites(
    session: Session,
    state: State,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
) -> list[SiteOut]:
    return [await site_out(session, state, s) for s in await sites.find_sites_near(session, lat, lon)]


@router.get("/sites")
async def list_sites(_: Inspector, session: Session, state: State) -> list[SiteOut]:
    return [await site_out(session, state, s) for s in await sites.list_sites(session)]


@router.get("/sites/{site_id}", dependencies=[Depends(public)])
async def get_site(site_id: UUID, session: Session, state: State) -> SiteOut:
    return await site_out(session, state, await sites.get_site(session, site_id))


@router.get("/facades/{facade_id}/baseline", dependencies=[Depends(public)])
async def baseline_image(facade_id: UUID, session: Session, state: State) -> RedirectResponse:
    baseline = await sites.primary_baseline(session, facade_id)
    return RedirectResponse(state.store.presigned_url(baseline.object_key), status_code=307)
