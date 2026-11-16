from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk, utc_now


class UserRow(UuidPk, Timestamped, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(16))
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessionRow(Base):
    __tablename__ = "sessions"

    id_hash: Mapped[bytes] = mapped_column(LargeBinary(32), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditLogRow(UuidPk, Base):
    __tablename__ = "audit_log"

    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    request_id: Mapped[str | None] = mapped_column(String(64))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class LlmCallRow(UuidPk, Base):
    __tablename__ = "llm_calls"

    observation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("observations.id", ondelete="SET NULL"), index=True
    )
    agent: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    cost_usd: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[int]
    status: Mapped[str] = mapped_column(String(16))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
