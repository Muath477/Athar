import json

from ml.data.build_dataset import DEFAULT_RATIOS, SPLITS, assign_splits, build, split_athar
from ml.tests.conftest import map_record


def test_every_site_lands_in_exactly_one_split_and_the_assignment_is_stable():
    sizes = {f"site-{i}": 3 + i % 4 for i in range(30)}
    first = assign_splits(sizes, DEFAULT_RATIOS, "seed")
    assert first == assign_splits(sizes, DEFAULT_RATIOS, "seed")
    assert set(first) == set(sizes)
    share = {
        s: sum(sizes[g] for g, split in first.items() if split == s) / sum(sizes.values()) for s in SPLITS
    }
    assert 0.7 <= share["train"] <= 0.9
    assert share["val"] > 0 and share["test"] > 0


def test_three_sites_give_one_site_to_each_split():
    assert sorted(assign_splits({"a": 5, "b": 5, "c": 5}, DEFAULT_RATIOS, "s").values()) == [
        "test",
        "train",
        "val",
    ]


def test_weak_labels_only_train_and_never_from_held_out_sites_or_the_model_itself():
    expert = [map_record(f"e{i}", f"site-{i}") for i in range(10)]
    splits = split_athar(expert, DEFAULT_RATIOS, "seed")
    held_out = {r["site_id"] for s in ("val", "test") for r in splits[s]}
    some_held_out = sorted(held_out)[0]
    weak = [
        map_record("w1", "site-new", quality="weak"),
        map_record("w2", some_held_out, quality="weak"),
        map_record("w3", "site-new", quality="weak", detector="qwen"),
    ]
    splits = split_athar(expert + weak, DEFAULT_RATIOS, "seed")
    weak_ids = {r["map_id"] for s in SPLITS for r in splits[s] if r["label_quality"] == "weak"}
    assert weak_ids == {"w1"}
    assert any(r["map_id"] == "w1" for r in splits["train"])


def test_build_writes_three_files_without_site_leakage(athar_export, tmp_path):
    out = tmp_path / "build"
    report = build(athar_export, [], out, cap=10, seed="seed")
    rows = {s: [json.loads(line) for line in (out / f"{s}.jsonl").read_text().splitlines()] for s in SPLITS}
    groups = {s: {r["group"] for r in rows[s]} for s in SPLITS}
    assert not groups["train"] & groups["test"] and not groups["train"] & groups["val"]
    assert sum(len(r) for r in rows.values()) == 20
    assert report["train"]["elements_by_type"]["crack"] == len(rows["train"])
    assert rows["test"][0]["meta"]["detector_cells"]
    assert (out / "report.md").read_text().startswith("| split |")
