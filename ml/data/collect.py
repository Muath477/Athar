import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from ml.data.fetch import DATA_DIR, FetchError, fetch
from ml.data.masks import crack_lines
from ml.data.sources import DEFAULT_KEYS, SOURCES, SOURCES_BY_KEY, LabelKind, Source

PUBLIC_DIR = DATA_DIR / "public"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
MASK_FOLDER_WORDS = ("mask", "label", "annot", "gt", "bw", "groundtruth")


def organise(source: Source) -> Path:
    root = fetch(source)
    if source.label_kind is LabelKind.CRACK_LINES:
        rows = _segmentation_rows(source, root)
    else:
        rows = _tag_rows(source, root)
    manifest = PUBLIC_DIR / f"{source.key}.jsonl"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return manifest


def normalised(part: str) -> str:
    return re.sub(r"[\s_\-]+", " ", part.lower()).strip()


def labels_for(source: Source, relative: Path) -> tuple[str, ...] | None:
    for part in reversed([normalised(p) for p in relative.parts[:-1]]):
        for word, damage_types in source.folder_labels:
            if part == word or part.startswith(word):
                return damage_types
    return None


def _tag_rows(source: Source, root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        relative = path.relative_to(root)
        damage_types = labels_for(source, relative)
        if damage_types is None:
            continue
        rows.append(
            {
                "source": source.key,
                "task": LabelKind.PATCH_TAGS.value,
                "image": str(path.relative_to(DATA_DIR)),
                "damage_types": list(damage_types),
                "group": f"{source.key}:{relative.parent}",
            }
        )
    return rows


def _segmentation_rows(source: Source, root: Path) -> list[dict[str, Any]]:
    images: dict[str, Path] = {}
    masks: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        folders = " ".join(part.lower() for part in path.relative_to(root).parts[:-1])
        (masks if any(word in folders for word in MASK_FOLDER_WORDS) else images)[path.stem] = path
    rows = []
    for stem, image in images.items():
        mask = masks.get(stem)
        if mask is None:
            continue
        rows.append(
            {
                "source": source.key,
                "task": LabelKind.CRACK_LINES.value,
                "image": str(image.relative_to(DATA_DIR)),
                "lines": crack_lines(mask),
                "group": f"{source.key}:{stem}",
            }
        )
    return rows


def summary(manifest: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in manifest.read_text().splitlines():
        row = json.loads(line)
        if row["task"] == LabelKind.CRACK_LINES.value:
            counts["crack_lines"] += 1
        else:
            counts[",".join(row["damage_types"]) or "sound"] += 1
    return counts


def chosen(only: list[str] | None, *, everything: bool) -> list[Source]:
    if only:
        unknown = sorted(set(only) - set(SOURCES_BY_KEY))
        if unknown:
            raise SystemExit(f"Unknown sources: {', '.join(unknown)}")
        return [SOURCES_BY_KEY[key] for key in only]
    if everything:
        return list(SOURCES)
    return [SOURCES_BY_KEY[key] for key in DEFAULT_KEYS]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and organise public wall damage datasets")
    parser.add_argument("command", choices=["list", "organise"])
    parser.add_argument("--only", nargs="*", help="source keys; the default sources when left out")
    parser.add_argument("--all", action="store_true", help="include the opt-in sources")
    parser.add_argument("--keep-going", action="store_true", help="report a failed source and continue")
    args = parser.parse_args()
    sources = chosen(args.only, everything=args.all)
    if args.command == "list":
        for source in SOURCES:
            mark = "default" if source.by_default else "opt-in"
            print(f"{source.key:26} {mark:8} {source.licence[:22]:24} {source.page}")
        return
    failed = []
    for source in sources:
        try:
            manifest = organise(source)
        except (FetchError, OSError) as error:
            if not args.keep_going:
                raise
            failed.append(source.key)
            print(f"{source.key}: skipped ({error})")
            continue
        print(f"{source.key}: {dict(summary(manifest))} -> {manifest.relative_to(DATA_DIR)}")
    if failed:
        print(f"Not organised: {', '.join(failed)}")


if __name__ == "__main__":
    main()
