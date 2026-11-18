import json
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from ml.data.sources import (
    DirectFile,
    HubDataset,
    HubLayout,
    ManualDownload,
    MendeleyFiles,
    Source,
)

DATA_DIR = Path(__file__).resolve().parent
RAW_DIR = DATA_DIR / "raw"
ARCHIVE_SUFFIXES = (".zip", ".rar", ".7z")
MENDELEY_FILES = "https://data.mendeley.com/public-api/datasets/{id}/files?folder_id=root&version={version}"
TIMEOUT_S = 300


class FetchError(SystemExit):
    pass


def source_dir(source: Source) -> Path:
    return RAW_DIR / source.key


def extracted_dir(source: Source) -> Path:
    return source_dir(source) / "extracted"


def fetch(source: Source) -> Path:
    match source.fetch:
        case DirectFile(url=url, archive=archive):
            download(url, source_dir(source) / archive)
        case MendeleyFiles(dataset_id=dataset_id, version=version):
            fetch_mendeley(source, dataset_id, version)
        case HubDataset() as hub:
            return fetch_hub(source, hub)
        case ManualDownload(archive=archive):
            target = source_dir(source) / archive
            if not target.exists():
                raise FetchError(
                    f"{source.key}: download {archive} by hand from {source.page} and place it at {target}"
                )
    return extract_all(source)


def download(url: str, target: Path) -> Path:
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    with urllib.request.urlopen(url, timeout=TIMEOUT_S) as response, partial.open("wb") as file:
        shutil.copyfileobj(response, file, length=1 << 20)
    partial.rename(target)
    return target


def mendeley_archives(listing: list[dict]) -> list[tuple[str, str]]:
    return [
        (item["filename"], item["download_url"])
        for item in listing
        if str(item.get("filename", "")).lower().endswith(ARCHIVE_SUFFIXES)
    ]


def fetch_mendeley(source: Source, dataset_id: str, version: int) -> None:
    url = MENDELEY_FILES.format(id=dataset_id, version=version)
    with urllib.request.urlopen(url, timeout=60) as response:
        listing = json.load(response)
    archives = mendeley_archives(listing)
    if not archives:
        raise FetchError(f"{source.key}: no archive is published at {source.page}")
    for filename, download_url in archives:
        download(download_url, source_dir(source) / PurePosixPath(filename).name)


def fetch_hub(source: Source, hub: HubDataset) -> Path:
    from huggingface_hub import snapshot_download

    local = source_dir(source) / "hub"
    snapshot_download(
        repo_id=hub.repo_id,
        repo_type="dataset",
        revision=hub.revision,
        local_dir=str(local),
        allow_patterns=list(hub.allow_patterns) or None,
    )
    if hub.layout is HubLayout.FILES:
        return local
    return parquet_answers_to_folders(sorted(local.rglob("*.parquet")), extracted_dir(source))


def parquet_answers_to_folders(parquet_files: list[Path], destination: Path) -> Path:
    import pyarrow.parquet as pq

    if destination.exists():
        return destination
    partial = destination.with_name(destination.name + ".part")
    shutil.rmtree(partial, ignore_errors=True)
    for parquet in parquet_files:
        table = pq.read_table(parquet, columns=["image", "answer"])
        for index, (image, answer) in enumerate(
            zip(table.column("image").to_pylist(), table.column("answer").to_pylist(), strict=True)
        ):
            folder = partial / folder_name(answer)
            folder.mkdir(parents=True, exist_ok=True)
            suffix = PurePosixPath(image.get("path") or "x.jpg").suffix or ".jpg"
            (folder / f"{parquet.stem}-{index:05d}{suffix}").write_bytes(image["bytes"])
    partial.rename(destination)
    return destination


def folder_name(answer: str) -> str:
    return "_".join(answer.strip().lower().split()) or "unlabelled"


def extract_all(source: Source) -> Path:
    destination = extracted_dir(source)
    if destination.exists():
        return destination
    partial = destination.with_name(destination.name + ".part")
    shutil.rmtree(partial, ignore_errors=True)
    archives = sorted(p for p in source_dir(source).iterdir() if p.suffix.lower() in ARCHIVE_SUFFIXES)
    if not archives:
        raise FetchError(f"{source.key}: nothing to extract in {source_dir(source)}")
    for archive in archives:
        extract(archive, partial / archive.stem)
    for nested in sorted(p for p in partial.rglob("*") if p.suffix.lower() in ARCHIVE_SUFFIXES):
        extract(nested, nested.with_suffix(""))
        nested.unlink()
    partial.rename(destination)
    return destination


def extract(archive: Path, destination: Path) -> None:
    suffix = archive.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            check_members(archive, [member.filename for member in bundle.infolist()])
            bundle.extractall(destination)
        return
    unrar = shutil.which("unrar")
    if suffix == ".rar" and unrar is not None:
        listing = _run([unrar, "lb", str(archive)]).splitlines()
        check_members(archive, listing)
        destination.mkdir(parents=True, exist_ok=True)
        _run([unrar, "x", "-o+", "-idq", str(archive), f"{destination}/"])
        return
    seven_zip = shutil.which("7z")
    if seven_zip is None:
        raise FetchError(f"{archive.name} needs unrar or 7-Zip: apt-get install -y unrar p7zip-full")
    listing = _run([seven_zip, "l", "-slt", "-ba", str(archive)]).splitlines()
    check_members(archive, [line[7:] for line in listing if line.startswith("Path = ")])
    _run([seven_zip, "x", "-y", f"-o{destination}", str(archive)])


def _run(command: list[str]) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def check_members(archive: Path, members: list[str]) -> None:
    for name in members:
        path = PurePosixPath(name.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise FetchError(f"{archive.name} holds a path outside the archive: {name}")
