import pytest

import sadu.shared.orm_registry  # noqa: F401  (registers every table so foreign keys resolve)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
