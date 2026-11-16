"""Integration tests run against the Postgres from docker compose, migrated to head.

Each test runs inside one outer transaction that is rolled back, so tests never see each
other's rows and the database stays clean.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sadu.modules.agents import api as agents
from sadu.modules.sites import api as sites
from sadu.shared.config import get_settings
from sadu.shared.db import Base
from sadu.shared.web import UnitOfWork
from tests.fakes import MemoryStore

PACK_DIR = Path(__file__).resolve().parents[3] / "region-packs" / "demo"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if Path(item.path).is_relative_to(Path(__file__).parent):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.anyio)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            async with AsyncSession(
                bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
            ) as db:
                yield db
            await transaction.rollback()
    except OperationalError as error:
        pytest.skip(f"Postgres not reachable: {error}")
    finally:
        await engine.dispose()


@pytest.fixture
async def committed_unit_of_work() -> AsyncIterator[UnitOfWork]:
    """Real commits through separate sessions, as in production; every table is emptied afterwards."""
    url = get_settings().database_url
    if not url.rsplit("/", 1)[-1].endswith("_test"):
        pytest.skip("committed tests run only against a database whose name ends in _test")
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def unit_of_work() -> AsyncIterator[AsyncSession]:
        async with factory() as db, db.begin():
            yield db

    try:
        yield unit_of_work
    finally:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        async with engine.begin() as connection:
            await connection.execute(text(f"TRUNCATE {tables} CASCADE"))
        await engine.dispose()


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


@dataclass(frozen=True)
class DemoSite:
    site: sites.SiteView
    facades: dict[str, sites.FacadeView]


@pytest.fixture
async def demo(session: AsyncSession, store: MemoryStore) -> DemoSite:
    [slug] = await agents.seed_region_pack(session, store, PACK_DIR)
    site = await sites.get_site_by_slug(session, slug)
    facades = {f.code: f for f in await sites.list_facades(session, site.id)}
    return DemoSite(site, facades)
