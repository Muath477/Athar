"""Integration tests run against the Postgres from docker compose, migrated to head.

Each test runs inside one outer transaction that is rolled back, so tests never see each
other's rows and the database stays clean.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from sadu.modules.sites import api as sites
from sadu.shared.config import get_settings
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
def store() -> MemoryStore:
    return MemoryStore()


@dataclass(frozen=True)
class DemoSite:
    site: sites.SiteView
    facades: dict[str, sites.FacadeView]


@pytest.fixture
async def demo(session: AsyncSession, store: MemoryStore) -> DemoSite:
    [slug] = await sites.import_region_pack(session, store, PACK_DIR)
    site = await sites.get_site_by_slug(session, slug)
    facades = {f.code: f for f in await sites.list_facades(session, site.id)}
    return DemoSite(site, facades)
