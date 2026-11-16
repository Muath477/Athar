import os

import pytest

# Tests never touch the development database; CI and local runs point at a separate one.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://sadu:dev@localhost:5432/sadu_test")

import sadu.shared.orm_registry  # noqa: F401  (registers every table so foreign keys resolve)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
