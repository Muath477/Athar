import json

from ml.data.target import Task, chat, crack_lines_target, patch_tags_target, wall_map_target
from ml.tests.conftest import CRACK, LOSS
from sadu.modules.mapping.application.element_prompt import SYSTEM_PROMPT, parse_answer


def test_wall_map_target_is_compact_strict_json_the_detector_accepts():
    target = wall_map_target([CRACK, LOSS])
    assert " " not in target.replace("plaster_loss", "")
    answer = json.loads(target)
    assert answer["elements"][0] == {
        "damage_type": "crack",
        "geometry": "line",
        "points": [[0.1, 0.1], [0.1, 0.4]],
        "severity": "moderate",
        "damage_class": "from_1_to_5mm",
        "confidence": "high",
    }
    assert [e.damage_type.value for e in parse_answer(target)] == ["crack", "plaster_loss"]


def test_damage_outside_the_mapped_types_is_left_out_of_targets():
    moisture = {**LOSS, "id": "E3", "damage_type": "moisture"}
    assert [e["damage_type"] for e in json.loads(wall_map_target([moisture, CRACK]))["elements"]] == ["crack"]


def test_chat_rows_carry_the_image_path_and_the_product_prompt():
    messages = chat(Task.WALL_MAP, "athar/images/m1.jpg", "{}")
    assert [m["role"] for m in messages] == ["system", "user", "assistant"]
    assert messages[0]["content"][0]["text"] == SYSTEM_PROMPT
    assert messages[1]["content"][0] == {"type": "image", "image": "athar/images/m1.jpg"}


def test_auxiliary_targets():
    assert patch_tags_target(["crack", "crack"]) == '{"damage_types":["crack"]}'
    assert json.loads(crack_lines_target([[(0.12345, 0.5), (0.9, 0.5)]]))["elements"][0]["points"] == [
        [0.123, 0.5],
        [0.9, 0.5],
    ]
