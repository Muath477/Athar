from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk


class DamageMapRow(UuidPk, Timestamped, Base):
    __tablename__ = "damage_maps"
    __table_args__ = (
        CheckConstraint("width_m > 0 AND height_m > 0", name="positive_size"),
        CheckConstraint(
            "status <> 'approved' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="approved_has_reviewer",
        ),
        Index("ix_damage_maps_facade_recent", "facade_id", text("created_at DESC")),
        Index("ix_damage_maps_site_recent", "site_id", text("created_at DESC")),
    )

    site_id: Mapped[UUID | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"))
    facade_id: Mapped[UUID | None] = mapped_column(ForeignKey("facades.id", ondelete="SET NULL"))
    wall_name: Mapped[str] = mapped_column(String(200))
    width_m: Mapped[float] = mapped_column(Float)
    height_m: Mapped[float] = mapped_column(Float)
    rows: Mapped[int]
    cols: Mapped[int]
    corners: Mapped[list[list[float]]] = mapped_column(JSONB)
    photo_key: Mapped[str] = mapped_column(String(300))
    rectified_key: Mapped[str] = mapped_column(String(300))
    rectified_width_px: Mapped[int]
    rectified_height_px: Mapped[int]
    detector: Mapped[str] = mapped_column(String(40))
    detector_status: Mapped[str] = mapped_column(String(16))
    summary_ar: Mapped[str] = mapped_column(Text, default="")
    model_cells: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(16))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DamageMapCellRow(Base):
    __tablename__ = "damage_map_cells"
    __table_args__ = (CheckConstraint('"row" >= 0 AND col >= 0', name="non_negative_cell"),)

    map_id: Mapped[UUID] = mapped_column(ForeignKey("damage_maps.id", ondelete="CASCADE"), primary_key=True)
    row: Mapped[int] = mapped_column(primary_key=True)
    col: Mapped[int] = mapped_column(primary_key=True)
    damage_type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))
