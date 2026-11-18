import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sadu.modules.capture.api import process_upload
from sadu.modules.mapping import api as mapping
from sadu.modules.mapping.domain.grid import CellRef, Grid, WallSize
from sadu.modules.mapping.domain.scoring import CellLabels, MapScore, ScoredPair, score_maps
from sadu.shared.adapters.anthropic_llm import AnthropicLLM
from sadu.shared.adapters.cached_llm import CachedLLM
from sadu.shared.config import get_settings
from sadu.shared.vocabulary import DamageType


@dataclass(frozen=True)
class LabelledWall:
    name: str
    photo: Path
    wall: WallSize
    quad: mapping.Quad
    rows: int
    expected: dict[str, str]


def load_case(label_file: Path, default_rows: int) -> LabelledWall:
    data: dict[str, Any] = json.loads(label_file.read_text(encoding="utf-8"))
    corners = data.get("corners")
    return LabelledWall(
        name=label_file.stem,
        photo=label_file.with_suffix(".jpg"),
        wall=WallSize(float(data["width_m"]), float(data["height_m"])),
        quad=mapping.Quad.from_list(corners) if corners else mapping.Quad.full_frame(),
        rows=int(data.get("rows", default_rows)),
        expected=data["expected"],
    )


def labels(grid: Grid, cells: dict[str, str]) -> CellLabels:
    return {grid.parse(cell): DamageType(damage_type) for cell, damage_type in cells.items()}


async def predict(
    detector: mapping.DamageDetector, case: LabelledWall
) -> tuple[Grid, dict[CellRef, DamageType]]:
    photo = process_upload(case.photo.read_bytes()).jpeg
    prepared = mapping.prepare_wall(photo, case.quad, case.wall, case.rows)
    run = await mapping.detect_damage(detector, prepared)
    return prepared.grid, {cell.ref: cell.damage_type for cell in run.output.cells}


async def score_folder(folder: Path) -> MapScore:
    settings = get_settings()
    llm = CachedLLM(AnthropicLLM(settings), Path(settings.sadu_demo_cache_dir), prefer_cache=True)
    detector = mapping.build_detector(settings, llm)
    pairs = []
    for label_file in sorted(folder.glob("*.json")):
        case = load_case(label_file, settings.sadu_map_rows)
        grid, predicted = await predict(detector, case)
        expected = labels(grid, case.expected)
        pairs.append(ScoredPair(grid.rows * grid.cols, predicted, expected))
        print(f"{case.name}: predicted {len(predicted)} damaged cells, expected {len(expected)}")
    return score_maps(pairs)


def report(score: MapScore) -> None:
    accuracy = score.damaged_vs_sound_accuracy
    print(f"\nwalls: {score.maps}  cells: {score.cells}")
    print(f"damaged vs sound accuracy: {_percent(accuracy)}")
    print(f"{'type':<18}{'precision':>10}{'recall':>10}{'f1':>10}{'tp':>5}{'fp':>5}{'fn':>5}")
    for row in score.by_type:
        print(
            f"{row.damage_type:<18}{_percent(row.precision):>10}{_percent(row.recall):>10}"
            f"{_percent(row.f1):>10}{row.true_positives:>5}{row.false_positives:>5}{row.false_negatives:>5}"
        )


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score the configured damage detector on labelled wall photos."
    )
    parser.add_argument("folder", type=Path, help="folder with <name>.jpg and <name>.json label pairs")
    parser.add_argument("--min-accuracy", type=float, default=0.0)
    args = parser.parse_args()
    score = asyncio.run(score_folder(args.folder))
    report(score)
    accuracy = score.damaged_vs_sound_accuracy or 0.0
    return 0 if accuracy >= args.min_accuracy else 1


if __name__ == "__main__":
    sys.exit(main())
