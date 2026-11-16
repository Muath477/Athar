from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk


class MissionRow(UuidPk, Timestamped, Base):
    __tablename__ = "missions"
    __table_args__ = (Index("ix_missions_facade_status", "facade_id", "status"),)

    facade_id: Mapped[UUID] = mapped_column(ForeignKey("facades.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(String(32))
    finding_id: Mapped[UUID | None] = mapped_column(ForeignKey("findings.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default="open")
    instruction_ar: Mapped[str] = mapped_column(Text)
    reference_baseline_id: Mapped[UUID] = mapped_column(ForeignKey("baseline_photos.id"))
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fulfilled_by: Mapped[UUID | None] = mapped_column(ForeignKey("observations.id", ondelete="SET NULL"))
