import asyncio

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy.engine import Connection

from sadu.shared.db import get_engine
from sadu.shared.orm_registry import metadata

EXTERNAL_TABLES = {"spatial_ref_sys", "topology", "layer"}


def include_object(obj: object, name: str | None, type_: str, reflected: bool, compare_to: object) -> bool:
    if type_ == "table" and name is not None and (name in EXTERNAL_TABLES or name.startswith("checkpoint")):
        return False
    return bool(alembic_helpers.include_object(obj, name, type_, reflected, compare_to))


def run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=metadata,
        include_object=include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    async with get_engine().connect() as connection:
        await connection.run_sync(run_migrations)


asyncio.run(run_online())
