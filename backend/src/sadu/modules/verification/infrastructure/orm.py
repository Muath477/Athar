from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk


class FindingRow(UuidPk, Timestamped, Base):
    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint(
            "status <> 'published' OR (baseline_key IS NOT NULL AND photo_key IS NOT NULL "
            "AND diff_key IS NOT NULL AND existence_label IN ('confirmed', 'likely'))",
            name="published_has_evidence",
        ),
        Index(
            "ix_findings_published_by_facade",
            "facade_id",
            "severity",
            postgresql_where=text("status = 'published'"),
        ),
        Index("ix_findings_corroboration", "facade_id", "damage_type", text("created_at DESC")),
    )

    facade_id: Mapped[UUID] = mapped_column(ForeignKey("facades.id", ondelete="CASCADE"))
    observation_id: Mapped[UUID] = mapped_column(ForeignKey("observations.id", ondelete="CASCADE"))
    inspection_run_id: Mapped[UUID] = mapped_column(ForeignKey("inspection_runs.id", ondelete="CASCADE"))
    region_id: Mapped[int]
    damage_type: Mapped[str] = mapped_column(String(32))
    region_uv: Mapped[list[float]] = mapped_column(JSONB)
    pin_xyz: Mapped[list[float]] = mapped_column(JSONB)
    severity: Mapped[str] = mapped_column(String(16))
    existence_label: Mapped[str] = mapped_column(String(16))
    cause: Mapped[str | None] = mapped_column(String(200))
    cause_label: Mapped[str] = mapped_column(String(16), default="interpretation")
    status: Mapped[str] = mapped_column(String(16))
    confirmations: Mapped[int] = mapped_column(default=0)
    rationale_ar: Mapped[str] = mapped_column(Text, default="")
    reasons: Mapped[list[str]] = mapped_column(JSONB, default=list)
    baseline_key: Mapped[str | None] = mapped_column(String(300))
    photo_key: Mapped[str | None] = mapped_column(String(300))
    diff_key: Mapped[str | None] = mapped_column(String(300))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FindingConfirmationRow(Timestamped, Base):
    __tablename__ = "finding_confirmations"
    __table_args__ = (UniqueConstraint("finding_id", "contributor_hash"),)

    finding_id: Mapped[UUID] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True)
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True
    )
    contributor_hash: Mapped[str] = mapped_column(String(64))


class ReviewRow(UuidPk, Timestamped, Base):
    __tablename__ = "reviews"

    finding_id: Mapped[UUID] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(16))
    changes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    reason: Mapped[str] = mapped_column(Text, default="")
