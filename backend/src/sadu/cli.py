import argparse
import asyncio
import getpass
import os
from pathlib import Path

import sadu.shared.orm_registry
from sadu.modules.admin import api as admin
from sadu.modules.agents import api as agents
from sadu.shared.config import get_settings
from sadu.shared.db import get_engine, unit_of_work
from sadu.shared.storage import get_object_store


async def seed(pack: str) -> None:
    store = get_object_store()
    await store.ensure_bucket()
    pack_dir = Path(get_settings().sadu_region_packs_dir) / pack
    async with unit_of_work() as session:
        slugs = await agents.seed_region_pack(session, store, pack_dir)
    print(f"Imported {', '.join(slugs)} from {pack_dir}")


async def create_user(email: str, role: str) -> None:
    password = os.environ.get("SADU_NEW_USER_PASSWORD") or getpass.getpass("Password: ")
    if len(password) < admin.MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Password must be at least {admin.MIN_PASSWORD_LENGTH} characters")
    async with unit_of_work() as session:
        user = await admin.create_user(session, email, password, admin.Role(role))
    print(f"Created {user.role} {user.email}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="sadu")
    commands = parser.add_subparsers(dest="command", required=True)
    seed_parser = commands.add_parser("seed", help="import a region pack")
    seed_parser.add_argument("--pack", default="demo")
    user_parser = commands.add_parser("create-user", help="create a dashboard account")
    user_parser.add_argument("email")
    user_parser.add_argument(
        "--role", choices=[r.value for r in admin.Role], default=admin.Role.INSPECTOR.value
    )
    args = parser.parse_args()

    async def run() -> None:
        try:
            if args.command == "seed":
                await seed(args.pack)
            else:
                await create_user(args.email, args.role)
        finally:
            await get_engine().dispose()

    asyncio.run(run())


if __name__ == "__main__":
    main()
