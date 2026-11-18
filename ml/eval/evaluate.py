import argparse
import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sadu.modules.mapping.application.element_prompt import ELEMENT_TYPES, InvalidAnswer, parse_answer
from sadu.modules.mapping.domain.damage_map import CellSource, MapCell
from sadu.modules.mapping.domain.elements import Element, element_from_json, measure
from sadu.modules.mapping.domain.glossary import GLOSSARY, Geometry
from sadu.modules.mapping.domain.grid import CellRef, Grid, WallSize
from sadu.modules.mapping.domain.raster import cells_from_elements
from sadu.modules.mapping.domain.scoring import CellLabels, MapScore, ScoredPair, score_maps
from sadu.shared.vocabulary import DamageType

SELF_DETECTOR = "qwen"
MEASURE_UNITS = {Geometry.AREA: "m2", Geometry.LINE: "m", Geometry.POINT: "count"}


def evaluate_rows(rows: list[dict[str, Any]], predictions: list[dict[str, str]]) -> dict[str, Any]:
    answers = {p["id"]: p["answer"] for p in predictions}
    model_pairs: list[ScoredPair] = []
    baselines: dict[str, list[tuple[ScoredPair, ScoredPair]]] = defaultdict(list)
    measured: list[tuple[WallSize, tuple[Element, ...], tuple[Element, ...]]] = []
    valid = 0
    for row in rows:
        meta = row["meta"]
        grid = Grid(meta["rows"], meta["cols"])
        expected = tuple(element_from_json(item) for item in meta["elements"])
        predicted = _parsed(answers.get(row["id"], ""))
        valid += predicted is not None
        predicted = predicted or ()
        truth = _labels(cells_from_elements(expected, grid, CellSource.EXPERT))
        model_pair = ScoredPair(grid.rows * grid.cols, _labels(cells_from_elements(predicted, grid)), truth)
        model_pairs.append(model_pair)
        measured.append((WallSize(meta["width_m"], meta["height_m"]), expected, predicted))
        if meta["detector"] != SELF_DETECTOR and meta["detector_status"] == "ok":
            baseline = ScoredPair(model_pair.total_cells, _detector_labels(meta["detector_cells"]), truth)
            baselines[meta["detector"]].append((baseline, model_pair))
    return {
        "test_maps": len(rows),
        "json_valid_rate": valid / len(rows) if rows else None,
        **summary(score_maps(model_pairs)),
        "measure_error": measure_errors(measured),
        "baselines": {
            detector: {
                "maps": len(pairs),
                "baseline": summary(score_maps(b for b, _ in pairs)),
                "model": summary(score_maps(m for _, m in pairs)),
            }
            for detector, pairs in baselines.items()
        },
    }


def summary(score: MapScore) -> dict[str, Any]:
    by_type = [s for s in score.by_type if s.damage_type in ELEMENT_TYPES]
    f1s = [s.f1 for s in by_type if s.f1 is not None]
    tp = sum(s.true_positives for s in by_type)
    fp = sum(s.false_positives for s in by_type)
    fn = sum(s.false_negatives for s in by_type)
    return {
        "macro_f1": sum(f1s) / len(f1s) if f1s else None,
        "micro_f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None,
        "damaged_vs_sound_accuracy": score.damaged_vs_sound_accuracy,
        "by_type": {
            s.damage_type.value: {
                "precision": s.precision,
                "recall": s.recall,
                "f1": s.f1,
                "support": s.true_positives + s.false_negatives,
            }
            for s in by_type
        },
    }


def measure_errors(
    maps: Iterable[tuple[WallSize, tuple[Element, ...], tuple[Element, ...]]],
) -> dict[str, dict[str, Any]]:
    sums: dict[DamageType, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    for wall, expected, predicted in maps:
        for damage_type in ELEMENT_TYPES:
            truth = _total(expected, damage_type, wall)
            guess = _total(predicted, damage_type, wall)
            if truth == 0 and guess == 0:
                continue
            totals = sums[damage_type]
            totals[0] += abs(guess - truth)
            totals[1] += truth
            totals[2] += 1
    return {
        damage_type.value: {
            "unit": MEASURE_UNITS[GLOSSARY[damage_type].geometry],
            "mean_abs_error": error / maps_seen,
            "relative_error": error / truth if truth else None,
            "maps": int(maps_seen),
        }
        for damage_type, (error, truth, maps_seen) in sums.items()
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        f"Test maps: {report['test_maps']}, valid JSON: {_percent(report['json_valid_rate'])}, "
        f"macro F1: {_number(report['macro_f1'])}, micro F1: {_number(report['micro_f1'])}",
        "",
        "| type | precision | recall | F1 | cells |",
        "|---|---|---|---|---|",
    ]
    for damage_type, row in report["by_type"].items():
        lines.append(
            f"| {damage_type} | {_number(row['precision'])} | {_number(row['recall'])} "
            f"| {_number(row['f1'])} | {row['support']} |"
        )
    for detector, comparison in report["baselines"].items():
        lines += [
            "",
            f"Same {comparison['maps']} test maps, fine-tuned model against the `{detector}` detector:",
            "",
            f"| type | F1 {detector} | F1 model |",
            "|---|---|---|",
        ]
        for damage_type, row in comparison["model"]["by_type"].items():
            other = comparison["baseline"]["by_type"][damage_type]
            lines.append(f"| {damage_type} | {_number(other['f1'])} | {_number(row['f1'])} |")
        baseline_macro = _number(comparison["baseline"]["macro_f1"])
        lines.append(f"| macro | {baseline_macro} | {_number(comparison['model']['macro_f1'])} |")
    return "\n".join(lines) + "\n"


def _parsed(answer: str) -> tuple[Element, ...] | None:
    try:
        return parse_answer(answer)
    except InvalidAnswer:
        return None


def _labels(cells: Iterable[MapCell]) -> CellLabels:
    return {cell.ref: cell.damage_type for cell in cells}


def _detector_labels(cells: Iterable[dict[str, Any]]) -> CellLabels:
    return {CellRef(int(c["row"]), int(c["col"])): DamageType(c["damage_type"]) for c in cells}


def _total(elements: Iterable[Element], damage_type: DamageType, wall: WallSize) -> float:
    total = 0.0
    for element in elements:
        if element.damage_type is not damage_type:
            continue
        size = measure(element, wall)
        total += size.area_m2 + size.length_m + size.count
    return total


def _number(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.1%}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Score model answers on the test split")
    parser.add_argument("--test", type=Path, default=Path("ml/data/build/test.jsonl"))
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("ml/eval/metrics.json"))
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.test.read_text().splitlines() if line.strip()]
    rows = [row for row in rows if row["task"] == "wall_map"]
    predictions = [json.loads(line) for line in args.predictions.read_text().splitlines() if line.strip()]
    report = evaluate_rows(rows, predictions)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    args.out.with_suffix(".md").write_text(markdown(report))
    print(markdown(report))


if __name__ == "__main__":
    main()
