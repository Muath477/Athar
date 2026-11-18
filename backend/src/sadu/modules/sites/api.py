import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_X, ST_Y, ST_AsGeoJSON, ST_DWithin, ST_GeogFromText
from sqlalchemy import Row, Select, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.sites.domain.geometry import FacadePlane, Vec3, image_point_to_uv
from sadu.modules.sites.infrastructure import pack_import
from sadu.modules.sites.infrastructure.orm import BaselinePhotoRow, FacadeRow, SiteRow
from sadu.shared.errors import NotFound
from sadu.shared.storage import ObjectStore

DEFAULT_SEARCH_RADIUS_M = 200


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


@dataclass(frozen=True)
class SiteView:
    id: UUID
    slug: str
    name_ar: str
    name_en: str
    building_type: str
    model_key: str | None
    location: LatLon
    boundary: list[LatLon]
    field_photography_permitted: bool = False


@dataclass(frozen=True)
class FacadeView:
    id: UUID
    site_id: UUID
    code: str
    name_ar: str
    name_en: str
    outward_azimuth_deg: float
    corners: list[list[float]]
    default_camera: dict[str, Any]

    @property
    def plane(self) -> FacadePlane:
        return FacadePlane.from_corners([_vec3(c) for c in self.corners])

    def pin_position(self, uv: tuple[float, float]) -> tuple[float, float, float]:
        return self.plane.uv_to_xyz(*uv)


@dataclass(frozen=True)
class BaselineView:
    id: UUID
    facade_id: UUID
    object_key: str
    width: int
    height: int
    h_img_to_uv: list[list[float]]

    def to_uv(self, x: float, y: float) -> tuple[float, float]:
        return image_point_to_uv(self.h_img_to_uv, x, y)


async def find_sites_near(
    session: AsyncSession, lat: float, lon: float, radius_m: int = DEFAULT_SEARCH_RADIUS_M
) -> list[SiteView]:
    point = ST_GeogFromText(f"SRID=4326;POINT({float(lon)} {float(lat)})")
    rows = await session.execute(_select_sites().where(ST_DWithin(SiteRow.boundary, point, radius_m)))
    return [_site_view(row) for row in rows]


async def list_sites(session: AsyncSession) -> list[SiteView]:
    rows = await session.execute(_select_sites().order_by(SiteRow.slug))
    return [_site_view(row) for row in rows]


async def get_site(session: AsyncSession, site_id: UUID) -> SiteView:
    return await _one_site(session, _select_sites().where(SiteRow.id == site_id))


async def get_site_by_slug(session: AsyncSession, slug: str) -> SiteView:
    return await _one_site(session, _select_sites().where(SiteRow.slug == slug))


async def list_facades(session: AsyncSession, site_id: UUID) -> list[FacadeView]:
    rows = await session.scalars(
        select(FacadeRow).where(FacadeRow.site_id == site_id).order_by(FacadeRow.code)
    )
    return [_facade_view(row) for row in rows]


async def get_facade(session: AsyncSession, facade_id: UUID) -> FacadeView:
    row = await session.get(FacadeRow, facade_id)
    if row is None:
        raise NotFound("not_found")
    return _facade_view(row)


async def primary_baseline(session: AsyncSession, facade_id: UUID) -> BaselineView:
    row = await session.scalar(
        select(BaselinePhotoRow)
        .where(BaselinePhotoRow.facade_id == facade_id)
        .order_by(BaselinePhotoRow.is_primary.desc())
        .limit(1)
    )
    if row is None:
        raise NotFound("not_found")
    return BaselineView(row.id, row.facade_id, row.object_key, row.width, row.height, row.h_img_to_uv)


async def import_region_pack(session: AsyncSession, store: ObjectStore, pack_dir: Path) -> list[str]:
    return await pack_import.import_pack(session, store, pack_dir)


def _select_sites() -> Select[SiteRow, float, float, str]:
    location = cast(SiteRow.location, Geometry)
    return select(SiteRow, ST_Y(location), ST_X(location), ST_AsGeoJSON(SiteRow.boundary))


async def _one_site(session: AsyncSession, query: Select[SiteRow, float, float, str]) -> SiteView:
    row = (await session.execute(query)).one_or_none()
    if row is None:
        raise NotFound("not_found")
    return _site_view(row)


async def set_field_photography(session: AsyncSession, site_id: UUID, permitted: bool) -> SiteView:
    row = await session.get(SiteRow, site_id)
    if row is None:
        raise NotFound("not_found")
    row.field_photography_permitted = permitted
    await session.flush()
    return await get_site(session, site_id)


def _site_view(row: Row[SiteRow, float, float, str]) -> SiteView:
    site, lat, lon, boundary_geojson = row
    ring = json.loads(boundary_geojson)["coordinates"][0]
    return SiteView(
        site.id,
        site.slug,
        site.name_ar,
        site.name_en,
        site.building_type,
        site.model_key,
        LatLon(float(lat), float(lon)),
        [LatLon(float(point[1]), float(point[0])) for point in ring],
        bool(site.field_photography_permitted),
    )


def _facade_view(row: FacadeRow) -> FacadeView:
    return FacadeView(
        row.id,
        row.site_id,
        row.code,
        row.name_ar,
        row.name_en,
        row.outward_azimuth_deg,
        row.corners,
        row.default_camera,
    )


def _vec3(values: list[float]) -> Vec3:
    return (float(values[0]), float(values[1]), float(values[2]))
