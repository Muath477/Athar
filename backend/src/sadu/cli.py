import argparse
import asyncio
import getpass
import os
from pathlib import Path

import sadu.shared.orm_registry
from sadu.modules.admin import api as admin
from sadu.modules.agents import api as agents
from sadu.modules.ingest import api as ingest
from sadu.modules.reports import api as reports
from sadu.shared.config import get_settings
from sadu.shared.db import get_engine, unit_of_work
from sadu.shared.storage import get_object_store


async def seed(pack: str) -> None:
    store = get_object_store()
    await store.ensure_bucket()
    pack_dir = Path(get_settings().sadu_region_packs_dir) / pack
    async with unit_of_work() as session:
        slugs = await agents.seed_region_pack(session, store, pack_dir)
        if ingest.DEMO_SITE_SLUG in slugs and get_settings().sadu_demo_mode:
            camera = await ingest.seed_demo_camera(session)
            print(f"Demo camera ready: {camera.name_ar}")
    print(f"Imported {', '.join(slugs)} from {pack_dir}")


async def create_user(email: str, role: str) -> None:
    password = os.environ.get("SADU_NEW_USER_PASSWORD") or getpass.getpass("Password: ")
    if len(password) < admin.MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Password must be at least {admin.MIN_PASSWORD_LENGTH} characters")
    async with unit_of_work() as session:
        user = await admin.create_user(session, email, password, admin.Role(role))
    print(f"Created {user.role} {user.email}")


QUALITY_LINES = (
    ("findings_with_evidence", "published findings with baseline, photo and difference"),
    ("maps_with_evidence", "approved maps with photo, field inspection and approver"),
    ("photos_held_back", "photos sent back for a retake or more input"),
    ("findings_held_for_specialist", "findings held for a specialist or rejected"),
    ("specialist_rejections", "specialist reviews that rejected the finding"),
    ("maps_corrected_by_specialist", "approved maps the specialist corrected"),
)


async def quality() -> None:
    async with unit_of_work() as session:
        report = await reports.quality_report(session)
    for field_name, label in QUALITY_LINES:
        ratio = getattr(report, field_name)
        share = "-" if ratio.value is None else f"{ratio.value:.0%}"
        print(f"{label:<62}{ratio.hits:>5}/{ratio.total:<5}{share:>6}")
    verdict = {True: "yes", False: "NO", None: "not measured yet"}[report.every_report_has_evidence]
    print(f"{'every report that reached the dashboard has evidence':<62}{verdict:>17}")
    if report.every_report_has_evidence is False:
        raise SystemExit(1)


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
    commands.add_parser("quality", help="print evidence and review metrics from live data")
    args = parser.parse_args()

    async def run() -> None:
        try:
            if args.command == "seed":
                await seed(args.pack)
            elif args.command == "quality":
                await quality()
            else:
                await create_user(args.email, args.role)
        finally:
            await get_engine().dispose()

    asyncio.run(run())


if __name__ == "__main__":
    main()
