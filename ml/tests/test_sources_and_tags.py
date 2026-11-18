import json
from pathlib import Path

import pytest

from ml.data.build_dataset import PUBLIC_TEST, build, split_public
from ml.data.collect import labels_for
from ml.data.fetch import (
    FetchError,
    check_members,
    folder_name,
    mendeley_archives,
    parquet_answers_to_folders,
)
from ml.data.sources import (
    DEFAULT_KEYS,
    OPEN_LICENCES,
    PATCH_TAG_TYPES,
    SOURCES,
    SOURCES_BY_KEY,
    HubDataset,
)
from ml.eval.tags import evaluate_tags, parse_tags


def test_catalogue_keys_are_unique_and_defaults_have_open_licences():
    assert len(SOURCES_BY_KEY) == len(SOURCES)
    for key in DEFAULT_KEYS:
        assert SOURCES_BY_KEY[key].licence in OPEN_LICENCES, key
    assert not SOURCES_BY_KEY["bd3_building_defects"].by_default


def test_folder_labels_use_only_the_patch_glossary_and_hub_sources_are_pinned():
    for source in SOURCES:
        for _, damage_types in source.folder_labels:
            assert damage_types is None or set(damage_types) <= PATCH_TAG_TYPES, source.key
        if isinstance(source.fetch, HubDataset):
            assert len(source.fetch.revision) == 40, source.key


@pytest.mark.parametrize(
    ("key", "path", "expected"),
    [
        ("historical_cracks_cairo", "Historical Building Cracks/Non-Crack/1.jpg", ()),
        ("historical_cracks_cairo", "Historical Building Cracks/Crack/1.jpg", ("crack",)),
        ("kasbah_algiers", "test/Mold/a.jpg", None),
        ("kasbah_algiers", "test/Spall/a.jpg", ("plaster_loss",)),
        ("bd3_building_defects", "major_crack/a.jpg", ("crack",)),
        ("bd3_building_defects", "stain/a.jpg", None),
        ("panam_city", "Historic_Place_Dataset/Corroded Plastic/a.jpg", ("plaster_loss",)),
        ("darbhanga_fort", "Darbhanga_Fort/Background_images/a.jpg", ()),
    ],
)
def test_folders_map_to_glossary_tags_and_unknown_classes_are_dropped(key, path, expected):
    assert labels_for(SOURCES_BY_KEY[key], Path(path)) == expected


def test_only_archives_are_taken_from_a_mendeley_listing():
    listing = [
        {"filename": "data.rar", "download_url": "u1"},
        {"filename": "model.h5", "download_url": "u2"},
        {"filename": "test.ZIP", "download_url": "u3"},
    ]
    assert mendeley_archives(listing) == [("data.rar", "u1"), ("test.ZIP", "u3")]


@pytest.mark.parametrize("name", ["../escape.jpg", "/etc/passwd", "a/../../b.jpg", "..\\win.jpg"])
def test_archive_paths_outside_the_folder_are_refused(name):
    with pytest.raises(FetchError):
        check_members(Path("x.zip"), ["fine/a.jpg", name])


def test_hub_answers_become_folder_names():
    assert folder_name(" Major Crack ") == "major_crack"
    assert folder_name("") == "unlabelled"


def tag_row(index: int, task: str = "patch_tags") -> dict:
    return {"id": f"src:{index}", "task": task, "meta": {"source": "src", "damage_types": ["crack"]}}


def test_public_split_is_stable_and_crack_lines_stay_in_training():
    rows = [tag_row(i) for i in range(2000)] + [tag_row(i, "crack_lines") for i in range(2000, 2100)]
    first = split_public(rows, "seed")
    assert first == split_public(rows, "seed")
    assert 0.07 < len(first[PUBLIC_TEST]) / 2000 < 0.13
    assert 0.03 < len(first["val"]) / 2000 < 0.07
    assert all(r["task"] == "patch_tags" for r in first[PUBLIC_TEST] + first["val"])


def test_build_without_athar_maps_uses_public_rows_for_validation(tmp_path):
    manifest = tmp_path / "public" / "src.jsonl"
    manifest.parent.mkdir()
    records = [
        {
            "source": "src",
            "task": "patch_tags",
            "image": f"raw/src/{i}.jpg",
            "damage_types": ["crack"] if i % 2 else [],
            "group": "src:x",
        }
        for i in range(400)
    ]
    manifest.write_text("".join(json.dumps(r) + "\n" for r in records))
    report = build(tmp_path / "missing", [manifest], tmp_path / "build", cap=400, seed="s")
    assert report["test"]["examples"] == 0
    assert report["val"]["examples"] > 0 and report[PUBLIC_TEST]["examples"] > 0
    assert (tmp_path / "build" / f"{PUBLIC_TEST}.jsonl").exists()


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ('{"damage_types": ["crack", "mold"]}', frozenset({"crack"})),
        ('```json\n{"damage_types": []}\n```', frozenset()),
        ("The wall looks cracked.", None),
        ('{"damage_types": "crack"}', None),
    ],
)
def test_tag_answers_are_parsed_leniently_but_strictly_typed(answer, expected):
    assert parse_tags(answer) == expected


def test_tag_scores_count_exact_matches_and_per_type_errors():
    rows = [
        {"id": "a", "meta": {"source": "s1", "damage_types": ["crack"]}},
        {"id": "b", "meta": {"source": "s1", "damage_types": []}},
        {"id": "c", "meta": {"source": "s2", "damage_types": ["plaster_loss"]}},
    ]
    predictions = [
        {"id": "a", "answer": '{"damage_types": ["crack"]}'},
        {"id": "b", "answer": '{"damage_types": ["crack"]}'},
        {"id": "c", "answer": "no idea"},
    ]
    report = evaluate_tags(rows, predictions)
    assert report["exact_match"] == pytest.approx(1 / 3)
    assert report["json_valid_rate"] == pytest.approx(2 / 3)
    assert report["by_type"]["crack"]["precision"] == 0.5
    assert report["by_type"]["crack"]["recall"] == 1.0
    assert report["by_type"]["plaster_loss"]["recall"] == 0.0
    assert report["by_type"]["plaster_loss"]["f1"] is None
    assert report["by_source"]["s2"] == {"examples": 1, "exact_match": 0.0}


def test_parquet_answers_are_written_into_answer_folders(tmp_path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    table = pa.table(
        {
            "image": [{"bytes": b"jpg1", "path": "x.jpg"}, {"bytes": b"jpg2", "path": None}],
            "answer": ["minor_crack", "plain"],
        }
    )
    parquet = tmp_path / "train.parquet"
    pq.write_table(table, parquet)
    out = parquet_answers_to_folders([parquet], tmp_path / "extracted")
    assert sorted(p.relative_to(out).as_posix() for p in out.rglob("*.jpg")) == [
        "minor_crack/train-00000.jpg",
        "plain/train-00001.jpg",
    ]
