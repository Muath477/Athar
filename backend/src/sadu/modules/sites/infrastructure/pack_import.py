from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import cv2
import numpy as np
import structlog
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.sites.domain.geometry import FacadePlane
from sadu.modules.sites.infrastructure.orm import BaselinePhotoRow, FacadeRow, RegionPackRow, SiteRow
from sadu.shared.storage import ObjectStore

log = structlog.get_logger()

UV_CORNERS = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float32)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FacadeSpec(Strict):
    code: str = Field(pattern=r"^[a-z0-9_]+$")
    name_ar: str
    name_en: str
    outward_azimuth_deg: float = Field(ge=0, le=360)
    corners: list[list[float]] = Field(min_length=4, max_length=4)
    default_camera: dict[str, list[float]]

    @field_validator("corners")
    @classmethod
    def corners_are_points(cls, corners: list[list[float]]) -> list[list[float]]:
        if any(len(point) != 3 for point in corners):
            raise ValueError("each corner needs x, y, z")
        FacadePlane.from_corners([(p[0], p[1], p[2]) for p in corners])
        return corners


class FacadeMap(Strict):
    site_slug: str
    units: str = Field(pattern="^meters$")
    up_axis: str = Field(pattern="^Y$")
    facades: list[FacadeSpec] = Field(min_length=4, max_length=6)


class BaselineSpec(Strict):
    facade_code: str
    file: str
    captured_at: datetime | None = None
    corners_px: list[list[float]] = Field(min_length=4, max_length=4)
    is_primary: bool = True


class SiteSpec(Strict):
    slug: str
    name_ar: str
    name_en: str
    building_type: str
    location: list[float] = Field(min_length=2, max_length=2, description="[lon, lat]")
    boundary: list[list[float]] = Field(min_length=4)
    model_file: str | None = None
    facade_map_file: str | None = None
    baselines: list[BaselineSpec] = []
    sources_file: str | None = None

    @model_validator(mode="after")
    def baselines_need_facades(self) -> "SiteSpec":
        if self.baselines and self.facade_map_file is None:
            raise ValueError("baseline photos need a facade map")
        return self


class PackSpec(Strict):
    code: str
    name_ar: str
    name_en: str
    version: str
    sites: list[SiteSpec]


async def import_pack(session: AsyncSession, store: ObjectStore, pack_dir: Path) -> list[str]:
    spec = PackSpec.model_validate_json((pack_dir / "pack.json").read_text(encoding="utf-8"))
    pack = await _upsert_pack(session, spec)
    slugs = []
    for site_spec in spec.sites:
        await _import_site(session, store, pack_dir, pack.id, site_spec)
        slugs.append(site_spec.slug)
    log.info("region_pack_imported", pack=spec.code, sites=len(slugs))
    return slugs


async def _upsert_pack(session: AsyncSession, spec: PackSpec) -> RegionPackRow:
    pack = await session.scalar(select(RegionPackRow).where(RegionPackRow.code == spec.code))
    if pack is None:
        pack = RegionPackRow(code=spec.code)
        session.add(pack)
    pack.name_ar, pack.name_en, pack.version = spec.name_ar, spec.name_en, spec.version
    await session.flush()
    return pack


def _facades_for(pack_dir: Path, spec: SiteSpec) -> list[FacadeSpec]:
    if spec.facade_map_file is None:
        return []
    facade_map = FacadeMap.model_validate_json((pack_dir / spec.facade_map_file).read_text(encoding="utf-8"))
    if facade_map.site_slug != spec.slug:
        raise ValueError(f"Facade map is for {facade_map.site_slug}, not {spec.slug}")
    return facade_map.facades


async def _import_site(
    session: AsyncSession, store: ObjectStore, pack_dir: Path, pack_id: Any, spec: SiteSpec
) -> None:
    facades = _facades_for(pack_dir, spec)

    await session.execute(delete(SiteRow).where(SiteRow.slug == spec.slug))
    model_key = None
    if spec.model_file:
        model_key = f"models/{spec.slug}.glb"
        await store.put(model_key, (pack_dir / spec.model_file).read_bytes(), "model/gltf-binary")

    site = SiteRow(
        pack_id=pack_id,
        slug=spec.slug,
        name_ar=spec.name_ar,
        name_en=spec.name_en,
        building_type=spec.building_type,
        location=f"SRID=4326;POINT({spec.location[0]} {spec.location[1]})",
        boundary=_polygon_wkt(spec.boundary),
        model_key=model_key,
    )
    session.add(site)
    await session.flush()

    facade_ids: dict[str, UUID] = {}
    for facade in facades:
        row = FacadeRow(
            site_id=site.id,
            code=facade.code,
            name_ar=facade.name_ar,
            name_en=facade.name_en,
            outward_azimuth_deg=facade.outward_azimuth_deg,
            corners=facade.corners,
            default_camera=facade.default_camera,
            polygon_uv=None,
        )
        session.add(row)
        await session.flush()
        facade_ids[facade.code] = row.id

    for baseline in spec.baselines:
        await _import_baseline(
            session,
            store,
            pack_dir=pack_dir,
            slug=spec.slug,
            facade_id=facade_ids[baseline.facade_code],
            spec=baseline,
        )


async def _import_baseline(
    session: AsyncSession,
    store: ObjectStore,
    *,
    pack_dir: Path,
    slug: str,
    facade_id: UUID,
    spec: BaselineSpec,
) -> None:
    data = (pack_dir / spec.file).read_bytes()
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Baseline {spec.file} is not a readable image")
    height, width = image.shape[:2]
    homography = cv2.getPerspectiveTransform(np.array(spec.corners_px, dtype=np.float32), UV_CORNERS)
    key = f"baselines/{slug}/{spec.facade_code}-{Path(spec.file).stem}.jpg"
    await store.put(key, data, "image/jpeg")
    session.add(
        BaselinePhotoRow(
            facade_id=facade_id,
            object_key=key,
            captured_at=spec.captured_at or datetime.now(UTC),
            is_primary=spec.is_primary,
            width=width,
            height=height,
            h_img_to_uv=homography.tolist(),
        )
    )


def _polygon_wkt(ring: list[list[float]]) -> str:
    closed = ring if ring[0] == ring[-1] else [*ring, ring[0]]
    points = ", ".join(f"{lon} {lat}" for lon, lat in closed)
    return f"SRID=4326;POLYGON(({points}))"
