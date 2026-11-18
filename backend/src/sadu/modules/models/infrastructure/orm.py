from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk


class MlModelRow(UuidPk, Timestamped, Base):
    __tablename__ = "ml_models"
    __table_args__ = (
        UniqueConstraint("name", "version"),
        Index("ix_ml_models_one_active", "status", unique=True, postgresql_where=text("status = 'active'")),
    )

    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(40))
    base_model: Mapped[str] = mapped_column(String(200))
    adapter_uri: Mapped[str] = mapped_column(String(500))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(16))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
