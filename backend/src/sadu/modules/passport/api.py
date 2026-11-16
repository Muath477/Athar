import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.passport.infrastructure.orm import PassportEntryRow, PassportRow
from sadu.shared.errors import Unauthorized

TOKEN_BYTES = 32


@dataclass(frozen=True)
class PassportEntry:
    site_id: UUID
    observation_id: UUID | None
    stamped_at: datetime


@dataclass(frozen=True)
class PassportSummary:
    id: UUID
    created_at: datetime
    entries: list[PassportEntry]


async def create(session: AsyncSession) -> tuple[UUID, str]:
    token = secrets.token_urlsafe(TOKEN_BYTES)
    row = PassportRow(token_hash=_hash(token))
    session.add(row)
    await session.flush()
    return row.id, token


async def resolve(session: AsyncSession, token: str) -> UUID:
    row = await session.scalar(select(PassportRow).where(PassportRow.token_hash == _hash(token)))
    if row is None:
        raise Unauthorized("invalid_passport")
    row.last_seen_at = datetime.now(UTC)
    return row.id


async def record_entry(
    session: AsyncSession, passport_id: UUID, site_id: UUID, observation_id: UUID | None
) -> bool:
    existing = await session.scalar(
        select(PassportEntryRow.id).where(
            PassportEntryRow.passport_id == passport_id, PassportEntryRow.site_id == site_id
        )
    )
    if existing is not None:
        return False
    session.add(PassportEntryRow(passport_id=passport_id, site_id=site_id, observation_id=observation_id))
    await session.flush()
    return True


async def summary(session: AsyncSession, passport_id: UUID) -> PassportSummary:
    row = await session.get(PassportRow, passport_id)
    if row is None:
        raise Unauthorized("invalid_passport")
    entries = await session.scalars(
        select(PassportEntryRow)
        .where(PassportEntryRow.passport_id == passport_id)
        .order_by(PassportEntryRow.created_at)
    )
    return PassportSummary(
        row.id, row.created_at, [PassportEntry(e.site_id, e.observation_id, e.created_at) for e in entries]
    )


async def delete_passport(session: AsyncSession, passport_id: UUID) -> None:
    await session.execute(delete(PassportRow).where(PassportRow.id == passport_id))


def _hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()
