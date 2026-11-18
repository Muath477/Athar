import argparse
import getpass
import http.cookiejar
import json
import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
ATHAR_DIR = DATA_DIR / "athar"
EXPORT_PATH = "/api/v1/ml/training-export"


def download_export(base_url: str, email: str, password: str, *, weak: bool, destination: Path) -> Path:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    login = urllib.request.Request(
        f"{base_url}/api/v1/auth/login",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(login, timeout=30):
        pass
    query = "?weak=true" if weak else ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        opener.open(f"{base_url}{EXPORT_PATH}{query}", timeout=600) as response,
        destination.open("wb") as file,
    ):
        shutil.copyfileobj(response, file)
    return destination


def unpack(archive: Path, target: Path) -> int:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    root = target.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if not (target / member.filename).resolve().is_relative_to(root):
                raise SystemExit(f"Export holds a path outside the archive: {member.filename}")
        bundle.extractall(target)
    card = json.loads((target / "export.json").read_text())
    return int(card["examples"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Download expert-approved Athar maps for training")
    parser.add_argument("--url", default=os.environ.get("ATHAR_URL", "http://localhost:8000"))
    parser.add_argument("--email", default=os.environ.get("ATHAR_EMAIL"))
    parser.add_argument("--weak", action="store_true", help="also export unedited draft maps as weak labels")
    parser.add_argument("--archive", type=Path, help="unpack an export zip you already downloaded")
    args = parser.parse_args()
    archive = args.archive
    if archive is None:
        if not args.email:
            raise SystemExit(
                "Pass --email or set ATHAR_EMAIL for an account with the manage_models permission"
            )
        password = os.environ.get("ATHAR_PASSWORD") or getpass.getpass("Password: ")
        archive = download_export(
            args.url.rstrip("/"),
            args.email,
            password,
            weak=args.weak,
            destination=DATA_DIR / "athar-export.zip",
        )
    examples = unpack(archive, ATHAR_DIR)
    print(f"Unpacked {examples} maps into {ATHAR_DIR}")


if __name__ == "__main__":
    main()
