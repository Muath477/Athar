from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk


class SiteScanRow(UuidPk, Timestamped, Base):
    __tablename__ = "site_scans"
    __table_args__ = (
        CheckConstraint("score BETWEEN 0 AND 100", name="score_range"),
        CheckConstraint("valid_share BETWEEN 0 AND 1", name="valid_share_range"),
        Index("ix_site_scans_site_recent", "site_id", text("created_at DESC")),
    )

    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(40))
    is_sample: Mapped[bool]
    status: Mapped[str] = mapped_column(String(24))
    baseline_start: Mapped[date] = mapped_column(Date)
    baseline_end: Mapped[date] = mapped_column(Date)
    recent_start: Mapped[date] = mapped_column(Date)
    recent_end: Mapped[date] = mapped_column(Date)
    baseline_scenes: Mapped[int]
    recent_scenes: Mapped[int]
    valid_share: Mapped[float] = mapped_column(Float)
    score: Mapped[int]
    level: Mapped[str] = mapped_column(String(16))
    signals: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    before_key: Mapped[str | None] = mapped_column(String(300))
    after_key: Mapped[str | None] = mapped_column(String(300))
    change_key: Mapped[str | None] = mapped_column(String(300))
    acknowledged_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ground_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mission_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
