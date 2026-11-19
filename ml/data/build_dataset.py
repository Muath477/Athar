import argparse
import hashlib
import json
import os
import random
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ml.data.target import Task, chat, crack_lines_target, patch_tags_target, wall_map_target

DATA_DIR = Path(__file__).resolve().parent
SPLITS = ("train", "val", "test")
PUBLIC_TEST = "public_test"
DEFAULT_RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}
PUBLIC_TEST_SHARE = 0.1
PUBLIC_VAL_SHARE = 0.05
SELF_TRAINING_DETECTORS = frozenset({"qwen"})

Row = dict[str, Any]


def site_group(record: Row) -> str:
    return str(record.get("site_id") or record.get("facade_id") or record["map_id"])


def assign_splits(group_sizes: dict[str, int], ratios: dict[str, float], seed: str) -> dict[str, str]:
    total = sum(group_sizes.values())
    filled = dict.fromkeys(SPLITS, 0)
    assignment = {}
    for group in sorted(group_sizes, key=lambda g: hashlib.sha256(f"{seed}:{g}".encode()).hexdigest()):
        split = min(SPLITS, key=lambda s: (filled[s] / (ratios[s] * total), SPLITS.index(s)))
        assignment[group] = split
        filled[split] += group_sizes[group]
    return assignment


def wall_map_rows(records: Iterable[Row], image_root: str) -> list[Row]:
    rows = []
    for record in records:
        image = f"{image_root}/{record['image']}"
        rows.append(
            {
                "id": f"athar:{record['map_id']}",
                "task": Task.WALL_MAP.value,
                "label_quality": record["label_quality"],
                "group": site_group(record),
                "messages": chat(Task.WALL_MAP, image, wall_map_target(record["elements"])),
                "meta": {
                    "map_id": record["map_id"],
                    "rows": record["rows"],
                    "cols": record["cols"],
                    "width_m": record["width_m"],
                    "height_m": record["height_m"],
                    "elements": record["elements"],
                    "detector": record["detector"],
                    "detector_status": record["detector_status"],
                    "detector_cells": record["detector_cells"],
                },
            }
        )
    return rows


def split_athar(records: list[Row], ratios: dict[str, float], seed: str) -> dict[str, list[Row]]:
    expert = [r for r in records if r["label_quality"] == "expert"]
    weak = [
        r for r in records if r["label_quality"] == "weak" and r["detector"] not in SELF_TRAINING_DETECTORS
    ]
    sizes = Counter(site_group(r) for r in expert)
    assignment = assign_splits(dict(sizes), ratios, seed)
    splits: dict[str, list[Row]] = {s: [] for s in SPLITS}
    for record in expert:
        splits[assignment[site_group(record)]].append(record)
    for record in weak:
        if assignment.get(site_group(record), "train") == "train":
            splits["train"].append(record)
    return splits


def public_rows(manifest: Path, cap: int, seed: str) -> list[Row]:
    records = [json.loads(line) for line in manifest.read_text().splitlines() if line.strip()]
    rng = random.Random(f"{seed}:{manifest.stem}")
    rng.shuffle(records)
    damaged = [r for r in records if r.get("damage_types") or r.get("lines")]
    sound = [r for r in records if not (r.get("damage_types") or r.get("lines"))]
    sound_taken = min(len(sound), cap // 2)
    damaged_taken = min(len(damaged), cap - sound_taken)
    return [_public_row(record) for record in damaged[:damaged_taken] + sound[:sound_taken]]


def split_public(rows: list[Row], seed: str) -> dict[str, list[Row]]:
    parts: dict[str, list[Row]] = {"train": [], "val": [], PUBLIC_TEST: []}
    for row in rows:
        if row["task"] != Task.PATCH_TAGS.value:
            parts["train"].append(row)
            continue
        share = int(hashlib.sha256(f"{seed}:{row['id']}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        if share < PUBLIC_TEST_SHARE:
            parts[PUBLIC_TEST].append(row)
        elif share < PUBLIC_TEST_SHARE + PUBLIC_VAL_SHARE:
            parts["val"].append(row)
        else:
            parts["train"].append(row)
    return parts


def read_manifest(athar_dir: Path) -> list[Row]:
    manifest = athar_dir / "manifest.jsonl"
    if not manifest.exists():
        return []
    return [json.loads(line) for line in manifest.read_text().splitlines() if line.strip()]


def _public_row(record: Row) -> Row:
    task = Task(record["task"])
    if task is Task.CRACK_LINES:
        target = crack_lines_target(record["lines"])
    else:
        target = patch_tags_target(record["damage_types"])
    return {
        "id": f"{record['source']}:{record['image']}",
        "task": task.value,
        "label_quality": "public",
        "group": record["group"],
        "messages": chat(task, record["image"], target),
        "meta": {"source": record["source"], "damage_types": record.get("damage_types", [])},
    }


def balance_report(splits: dict[str, list[Row]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for split, rows in splits.items():
        elements: Counter[str] = Counter()
        tags: Counter[str] = Counter()
        tasks: Counter[str] = Counter()
        quality: Counter[str] = Counter()
        for row in rows:
            tasks[row["task"]] += 1
            quality[row["label_quality"]] += 1
            for element in row["meta"].get("elements", []):
                elements[element["damage_type"]] += 1
            if row["task"] == Task.PATCH_TAGS.value:
                tags.update(row["meta"]["damage_types"] or ["sound"])
        report[split] = {
            "examples": len(rows),
            "sites": len({row["group"] for row in rows if row["task"] == Task.WALL_MAP.value}),
            "tasks": dict(tasks),
            "label_quality": dict(quality),
            "elements_by_type": dict(sorted(elements.items())),
            "patch_tags": dict(sorted(tags.items())),
        }
    return report


def report_markdown(report: dict[str, Any]) -> str:
    types = sorted({t for split in report.values() for t in split["elements_by_type"]})
    header = ["split", "examples", "sites", *types]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for split, data in report.items():
        counts = [str(data["elements_by_type"].get(t, 0)) for t in types]
        lines.append("| " + " | ".join([split, str(data["examples"]), str(data["sites"]), *counts]) + " |")
    tag_types = sorted({t for split in report.values() for t in split["patch_tags"]})
    if tag_types:
        lines += ["", "| split | public close-ups | " + " | ".join(tag_types) + " |"]
        lines.append("|" + "---|" * (len(tag_types) + 2))
        for split, data in report.items():
            counts = " | ".join(str(data["patch_tags"].get(t, 0)) for t in tag_types)
            lines.append(f"| {split} | {data['tasks'].get(Task.PATCH_TAGS.value, 0)} | {counts} |")
    return "\n".join(lines) + "\n"


def write_jsonl(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def build(
    athar_dir: Path, public_manifests: list[Path], out_dir: Path, *, cap: int, seed: str
) -> dict[str, Any]:
    records = read_manifest(athar_dir)
    image_root = os.path.relpath(athar_dir, DATA_DIR)
    athar_splits = split_athar(records, DEFAULT_RATIOS, seed)
    splits = {split: wall_map_rows(rows, image_root) for split, rows in athar_splits.items()}
    athar_val_empty = not splits["val"]
    splits[PUBLIC_TEST] = []
    for public in public_manifests:
        parts = split_public(public_rows(public, cap, seed), seed)
        splits["train"] += parts["train"]
        splits[PUBLIC_TEST] += parts[PUBLIC_TEST]
        splits["val" if athar_val_empty else "train"] += parts["val"]
    random.Random(seed).shuffle(splits["train"])
    for split, rows in splits.items():
        write_jsonl(out_dir / f"{split}.jsonl", rows)
    report = balance_report(splits)
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (out_dir / "report.md").write_text(report_markdown(report))
    if not splits["train"]:
        raise SystemExit(
            f"train.jsonl has 0 rows: {len(records)} Athar records and {len(public_manifests)} public "
            "manifests went in. Scroll up to the 'collect organise' cell's own output and check each "
            "source's fetch error, then re-run this cell."
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build chat-format train/val/test files split by site")
    parser.add_argument("--athar", type=Path, default=DATA_DIR / "athar")
    parser.add_argument(
        "--public", type=Path, nargs="*", default=sorted((DATA_DIR / "public").glob("*.jsonl"))
    )
    parser.add_argument("--out", type=Path, default=DATA_DIR / "build")
    parser.add_argument(
        "--public-cap", type=int, default=1500, help="most examples taken from each public set"
    )
    parser.add_argument("--seed", default="athar-v1")
    args = parser.parse_args()
    report = build(args.athar, args.public, args.out, cap=args.public_cap, seed=args.seed)
    print(report_markdown(report))


if __name__ == "__main__":
    main()
