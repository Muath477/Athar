from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk, utc_now


class DeviceRow(UuidPk, Timestamped, Base):
    __tablename__ = "devices"
    __table_args__ = (CheckConstraint("interval_h IS NULL OR interval_h > 0", name="positive_interval"),)

    kind: Mapped[str] = mapped_column(String(16))
    name_ar: Mapped[str] = mapped_column(String(200))
    site_id: Mapped[UUID | None] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    facade_id: Mapped[UUID | None] = mapped_column(ForeignKey("facades.id", ondelete="SET NULL"))
    snapshot_url: Mapped[str | None] = mapped_column(String(500))
    rtsp_url: Mapped[str | None] = mapped_column(String(500))
    username: Mapped[str | None] = mapped_column(String(100))
    secret_env: Mapped[str | None] = mapped_column(String(100))
    interval_h: Mapped[int | None]
    active: Mapped[bool] = mapped_column(default=True)
    last_capture_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(16))
    last_error_ar: Mapped[str | None] = mapped_column(Text)
    last_photo_key: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class IngestJobRow(UuidPk, Timestamped, Base):
    __tablename__ = "ingest_jobs"
    __table_args__ = (
        Index("ix_ingest_jobs_due", "next_attempt_at", postgresql_where=text("status = 'queued'")),
        Index("ix_ingest_jobs_device_recent", "device_id", text("created_at DESC")),
    )

    batch_id: Mapped[UUID | None] = mapped_column(index=True)
    device_id: Mapped[UUID | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(16))
    source_label: Mapped[str | None] = mapped_column(String(200))
    file_name: Mapped[str] = mapped_column(String(200))
    photo_key: Mapped[str | None] = mapped_column(String(300))
    photo_ready: Mapped[bool] = mapped_column(default=False)
    site_id: Mapped[UUID | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"))
    facade_id: Mapped[UUID | None] = mapped_column(ForeignKey("facades.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16))
    attempts: Mapped[int] = mapped_column(default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    error_code: Mapped[str | None] = mapped_column(String(40))
    error_ar: Mapped[str | None] = mapped_column(Text)
    photo_meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    map_id: Mapped[UUID | None] = mapped_column(ForeignKey("damage_maps.id", ondelete="SET NULL"))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
