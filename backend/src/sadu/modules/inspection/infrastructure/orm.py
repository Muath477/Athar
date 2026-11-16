from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk


class InspectionRunRow(UuidPk, Timestamped, Base):
    __tablename__ = "inspection_runs"

    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="CASCADE"), index=True
    )
    baseline_id: Mapped[UUID] = mapped_column(ForeignKey("baseline_photos.id"))
    quality: Mapped[dict[str, Any]] = mapped_column(JSONB)
    alignment: Mapped[dict[str, Any]] = mapped_column(JSONB)
    aligned_key: Mapped[str | None] = mapped_column(String(300))
    diff_key: Mapped[str | None] = mapped_column(String(300))
    regions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    judgment: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(64))
