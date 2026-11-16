from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache
from uuid import UUID, uuid4

from sqlalchemy import DateTime, MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sadu.shared.config import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UuidPk:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


def utc_now() -> datetime:
    return datetime.now(UTC)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


@asynccontextmanager
async def unit_of_work() -> AsyncIterator[AsyncSession]:
    """One transaction: commits on success, rolls back on any exception."""
    async with get_session_factory()() as session, session.begin():
        yield session


def plain_postgres_url() -> str:
    """libpq URL for psycopg and the LangGraph checkpointer (no SQLAlchemy driver prefix)."""
    return get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
