from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk, utc_now


class PassportRow(UuidPk, Timestamped, Base):
    __tablename__ = "passports"

    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PassportEntryRow(UuidPk, Timestamped, Base):
    __tablename__ = "passport_entries"

    passport_id: Mapped[UUID] = mapped_column(ForeignKey("passports.id", ondelete="CASCADE"), index=True)
    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"))
    observation_id: Mapped[UUID | None] = mapped_column(ForeignKey("observations.id", ondelete="SET NULL"))
