import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://sadu:dev@localhost:5432/sadu_test")

import sadu.shared.orm_registry


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
