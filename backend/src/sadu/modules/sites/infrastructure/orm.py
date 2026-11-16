from datetime import datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk


class RegionPackRow(UuidPk, Timestamped, Base):
    __tablename__ = "region_packs"

    code: Mapped[str] = mapped_column(String(64), unique=True)
    name_ar: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(32))


class SiteRow(UuidPk, Timestamped, Base):
    __tablename__ = "sites"

    pack_id: Mapped[UUID] = mapped_column(ForeignKey("region_packs.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name_ar: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    building_type: Mapped[str] = mapped_column(String(64))
    location: Mapped[Any] = mapped_column(Geography("POINT", srid=4326, spatial_index=True))
    boundary: Mapped[Any] = mapped_column(Geography("POLYGON", srid=4326, spatial_index=True))
    model_key: Mapped[str | None] = mapped_column(String(300))


class FacadeRow(UuidPk, Base):
    __tablename__ = "facades"
    __table_args__ = (UniqueConstraint("site_id", "code"),)

    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    name_ar: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    outward_azimuth_deg: Mapped[float] = mapped_column(Float)
    corners: Mapped[list[list[float]]] = mapped_column(JSONB)
    default_camera: Mapped[dict[str, Any]] = mapped_column(JSONB)
    polygon_uv: Mapped[list[list[float]] | None] = mapped_column(JSONB)


class BaselinePhotoRow(UuidPk, Base):
    __tablename__ = "baseline_photos"

    facade_id: Mapped[UUID] = mapped_column(ForeignKey("facades.id", ondelete="CASCADE"), index=True)
    object_key: Mapped[str] = mapped_column(String(300))
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_primary: Mapped[bool] = mapped_column(default=False)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    h_img_to_uv: Mapped[list[list[float]]] = mapped_column(JSONB)
