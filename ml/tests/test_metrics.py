import json

import pytest

from ml.data.build_dataset import wall_map_rows
from ml.data.target import wall_map_target
from ml.eval.evaluate import evaluate_rows, markdown
from ml.tests.conftest import CRACK, LOSS, map_record


def rows():
    return wall_map_rows([map_record("m1", "s1"), map_record("m2", "s2")], "athar")


def test_a_perfect_answer_scores_one_and_beats_a_weaker_baseline():
    test_rows = rows()
    perfect = [{"id": r["id"], "answer": wall_map_target([CRACK, LOSS])} for r in test_rows]
    report = evaluate_rows(test_rows, perfect)
    assert report["json_valid_rate"] == 1.0
    assert report["macro_f1"] == pytest.approx(1.0)
    assert report["by_type"]["crack"]["support"] == 2 * 2
    assert report["measure_error"]["crack"]["mean_abs_error"] == pytest.approx(0.0)
    comparison = report["baselines"]["grid_api"]
    assert comparison["maps"] == 2
    assert comparison["baseline"]["by_type"]["crack"]["precision"] == 1.0
    assert comparison["baseline"]["by_type"]["crack"]["recall"] == pytest.approx(0.5)
    assert comparison["model"]["macro_f1"] == pytest.approx(1.0)
    assert "| crack |" in markdown(report)


def test_invalid_or_missing_answers_count_as_empty_maps():
    test_rows = rows()
    answers = [{"id": test_rows[0]["id"], "answer": "not json"}]
    report = evaluate_rows(test_rows, answers)
    assert report["json_valid_rate"] == 0.0
    assert report["by_type"]["crack"]["recall"] == 0.0
    assert report["by_type"]["crack"]["precision"] is None


def test_length_and_area_errors_are_in_metres():
    test_rows = rows()[:1]
    longer = {**CRACK, "points": [[0.1, 0.1], [0.1, 0.6]]}
    report = evaluate_rows(test_rows, [{"id": test_rows[0]["id"], "answer": wall_map_target([longer, LOSS])}])
    crack = report["measure_error"]["crack"]
    assert crack["unit"] == "m"
    assert crack["mean_abs_error"] == pytest.approx(1.0)
    assert crack["relative_error"] == pytest.approx(1.0 / 1.5)
    assert json.dumps(report)
