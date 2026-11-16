from datetime import datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, UuidPk, utc_now


class ObservationRow(UuidPk, Base):
    __tablename__ = "observations"
    __table_args__ = (
        Index(
            "ix_observations_latest_per_facade",
            "facade_id",
            text("captured_at DESC"),
            postgresql_where=text("status = 'done'"),
        ),
    )

    site_id: Mapped[UUID | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"))
    facade_id: Mapped[UUID | None] = mapped_column(ForeignKey("facades.id", ondelete="SET NULL"))
    passport_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("passports.id", ondelete="SET NULL"), index=True
    )
    mission_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("missions.id", ondelete="SET NULL", use_alter=True)
    )
    object_key: Mapped[str] = mapped_column(String(300))
    width: Mapped[int]
    height: Mapped[int]
    location: Mapped[Any | None] = mapped_column(Geography("POINT", srid=4326, spatial_index=False))
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float)
    heading_deg: Mapped[float | None] = mapped_column(Float)
    heading_accuracy_deg: Mapped[float | None] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    status: Mapped[str] = mapped_column(String(32), default="received")
    status_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    faces_blurred: Mapped[int] = mapped_column(default=0)
    delete_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
