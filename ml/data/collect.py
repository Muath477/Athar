import argparse
import json
import shutil
import urllib.request
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ml.data.masks import crack_lines

DATA_DIR = Path(__file__).resolve().parent
RAW_DIR = DATA_DIR / "raw"
PUBLIC_DIR = DATA_DIR / "public"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
MASK_FOLDER_WORDS = ("mask", "label", "gt", "bw", "groundtruth")


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    licence: str
    page: str
    archive: str
    label_kind: str
    folder_labels: tuple[tuple[str, tuple[str, ...]], ...] = ()
    download: str | None = None


SOURCES: tuple[Source, ...] = (
    Source(
        key="sdnet2018",
        title="SDNET2018 concrete crack images (bridge decks, walls, pavements)",
        licence="CC BY 4.0",
        page="https://digitalcommons.usu.edu/all_datasets/48",
        archive="SDNET2018.zip",
        label_kind="patch_tags",
        folder_labels=(
            ("cd", ("crack",)),
            ("cw", ("crack",)),
            ("cp", ("crack",)),
            ("ud", ()),
            ("uw", ()),
            ("up", ()),
        ),
    ),
    Source(
        key="ozgenel_classification",
        title="Concrete Crack Images for Classification",
        licence="CC BY 4.0",
        page="https://data.mendeley.com/datasets/5y9wdsg2zt/2",
        archive="ozgenel_classification.zip",
        label_kind="patch_tags",
        folder_labels=(("positive", ("crack",)), ("negative", ())),
    ),
    Source(
        key="ozgenel_segmentation",
        title="Concrete Crack Segmentation Dataset",
        licence="CC BY 4.0",
        page="https://data.mendeley.com/datasets/jwsn7tfbrp/1",
        archive="ozgenel_segmentation.zip",
        label_kind="crack_lines",
    ),
    Source(
        key="rfsat_masonry",
        title="Dataset for Crack Detection in Images of Bricks and Masonry",
        licence="CC BY 4.0",
        page="https://zenodo.org/records/6870108",
        archive="Dataset (RFSAT).zip",
        label_kind="patch_tags",
        folder_labels=(("positive", ("crack",)), ("negative", ())),
        download="https://zenodo.org/records/6870108/files/Dataset%20(RFSAT).zip?download=1",
    ),
    Source(
        key="kasbah_algiers",
        title="Surface damage of heritage walls, Kasbah of Algiers",
        licence="CC BY 4.0",
        page="https://data.mendeley.com/datasets/zwshr65gnc/2",
        archive="kasbah_algiers.zip",
        label_kind="patch_tags",
        folder_labels=(
            ("efflorescence", ("salt_efflorescence",)),
            ("spall", ("plaster_loss",)),
            ("crack", ("crack",)),
            ("mold", ()),
        ),
    ),
)


def fetch(source: Source) -> Path:
    target = RAW_DIR / source.key / source.archive
    if target.exists():
        return target
    if source.download is None:
        raise SystemExit(
            f"{source.key}: download {source.archive} by hand from {source.page} "
            f"and place it at {target} (licence {source.licence})."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    with urllib.request.urlopen(source.download, timeout=120) as response, partial.open("wb") as file:
        shutil.copyfileobj(response, file)
    partial.rename(target)
    return target


def organise(source: Source) -> Path:
    archive = fetch(source)
    extracted = RAW_DIR / source.key / "extracted"
    if not extracted.exists():
        _safe_extract(archive, extracted)
    rows = (
        _segmentation_rows(source, extracted)
        if source.label_kind == "crack_lines"
        else _tag_rows(source, extracted)
    )
    manifest = PUBLIC_DIR / f"{source.key}.jsonl"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return manifest


def labels_for(source: Source, relative: Path) -> tuple[str, ...] | None:
    parts = [part.lower() for part in relative.parts[:-1]]
    for part in reversed(parts):
        for word, damage_types in source.folder_labels:
            if part == word or part.startswith(word):
                return damage_types
    return None


def _tag_rows(source: Source, extracted: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(extracted.rglob("*")):
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        relative = path.relative_to(extracted)
        damage_types = labels_for(source, relative)
        if damage_types is None:
            continue
        rows.append(
            {
                "source": source.key,
                "task": "patch_tags",
                "image": str(path.relative_to(DATA_DIR)),
                "damage_types": list(damage_types),
                "group": f"{source.key}:{relative.parent}",
            }
        )
    return rows


def _segmentation_rows(source: Source, extracted: Path) -> list[dict[str, Any]]:
    images: dict[str, Path] = {}
    masks: dict[str, Path] = {}
    for path in sorted(extracted.rglob("*")):
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        folders = " ".join(part.lower() for part in path.relative_to(extracted).parts[:-1])
        (masks if any(word in folders for word in MASK_FOLDER_WORDS) else images)[path.stem] = path
    rows = []
    for stem, image in images.items():
        mask = masks.get(stem)
        if mask is None:
            continue
        rows.append(
            {
                "source": source.key,
                "task": "crack_lines",
                "image": str(image.relative_to(DATA_DIR)),
                "lines": crack_lines(mask),
                "group": f"{source.key}:{stem}",
            }
        )
    return rows


def _safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(root):
                raise SystemExit(f"{archive.name} holds a path outside the archive: {member.filename}")
        bundle.extractall(destination)


def summary(manifest: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in manifest.read_text().splitlines():
        row = json.loads(line)
        if row["task"] == "crack_lines":
            counts["crack_lines"] += 1
        else:
            counts[",".join(row["damage_types"]) or "sound"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and organise public wall damage datasets")
    parser.add_argument("command", choices=["list", "organise"])
    parser.add_argument("--only", nargs="*", default=[s.key for s in SOURCES])
    args = parser.parse_args()
    chosen = [s for s in SOURCES if s.key in args.only]
    if args.command == "list":
        for source in chosen:
            print(f"{source.key:24} {source.licence:10} {source.page}")
        return
    for source in chosen:
        manifest = organise(source)
        print(f"{source.key}: {dict(summary(manifest))} -> {manifest.relative_to(DATA_DIR)}")


if __name__ == "__main__":
    main()
