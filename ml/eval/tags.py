import json
from collections import Counter, defaultdict
from typing import Any

from ml.data.sources import PATCH_TAG_TYPES

TAG_ORDER = tuple(sorted(PATCH_TAG_TYPES))


def parse_tags(answer: str) -> frozenset[str] | None:
    start, end = answer.find("{"), answer.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(answer[start : end + 1])
    except json.JSONDecodeError:
        return None
    damage_types = parsed.get("damage_types") if isinstance(parsed, dict) else None
    if not isinstance(damage_types, list):
        return None
    return frozenset(str(t) for t in damage_types) & PATCH_TAG_TYPES


def evaluate_tags(rows: list[dict[str, Any]], predictions: list[dict[str, str]]) -> dict[str, Any]:
    answers = {p["id"]: p["answer"] for p in predictions}
    counts = {t: Counter() for t in TAG_ORDER}
    by_source: dict[str, Counter[str]] = defaultdict(Counter)
    valid = exact = 0
    for row in rows:
        truth = frozenset(row["meta"]["damage_types"])
        predicted = parse_tags(answers.get(row["id"], ""))
        valid += predicted is not None
        predicted = predicted or frozenset()
        hit = predicted == truth
        exact += hit
        source = by_source[row["meta"]["source"]]
        source["examples"] += 1
        source["exact"] += hit
        for damage_type in TAG_ORDER:
            outcome = _outcome(damage_type in predicted, damage_type in truth)
            if outcome:
                counts[damage_type][outcome] += 1
    total = len(rows)
    return {
        "examples": total,
        "json_valid_rate": valid / total if total else None,
        "exact_match": exact / total if total else None,
        "by_type": {t: _scores(counts[t]) for t in TAG_ORDER},
        "by_source": {
            key: {"examples": c["examples"], "exact_match": c["exact"] / c["examples"]}
            for key, c in sorted(by_source.items())
        },
    }


def _outcome(predicted: bool, expected: bool) -> str | None:
    if predicted and expected:
        return "tp"
    if predicted:
        return "fp"
    if expected:
        return "fn"
    return None


def _scores(counts: Counter[str]) -> dict[str, Any]:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    if precision is None or recall is None:
        f1 = None
    else:
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}


def comparison_markdown(before: dict[str, Any], after: dict[str, Any]) -> str:
    lines = [
        f"Held-out public close-ups: {after['examples']}",
        "",
        "| measure | base model | fine-tuned |",
        "|---|---|---|",
        f"| valid JSON | {_percent(before['json_valid_rate'])} | {_percent(after['json_valid_rate'])} |",
        f"| exact tag match | {_percent(before['exact_match'])} | {_percent(after['exact_match'])} |",
    ]
    for damage_type in TAG_ORDER:
        b, a = before["by_type"][damage_type], after["by_type"][damage_type]
        lines.append(
            f"| {damage_type} precision / recall | {_percent(b['precision'])} / {_percent(b['recall'])} "
            f"| {_percent(a['precision'])} / {_percent(a['recall'])} |"
        )
    lines += ["", "| source | examples | exact base | exact fine-tuned |", "|---|---|---|---|"]
    for key, row in after["by_source"].items():
        base = before["by_source"].get(key, {}).get("exact_match")
        lines.append(f"| {key} | {row['examples']} | {_percent(base)} | {_percent(row['exact_match'])} |")
    return "\n".join(lines) + "\n"


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.1%}"
