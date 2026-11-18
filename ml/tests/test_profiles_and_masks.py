from pathlib import Path

import numpy as np
import pytest

from ml.data.collect import SOURCES, labels_for
from ml.data.masks import lines_from_mask
from ml.data.target import wall_map_target
from ml.serve.http_bridge import detections
from ml.tests.conftest import CRACK, LOSS
from ml.train.profiles import fallback_ladder, load_config, pick_profile
from sadu.modules.mapping.application.element_prompt import parse_answer
from sadu.modules.mapping.infrastructure.http_detector import LabelMap, parse_detections


@pytest.mark.parametrize(
    ("vram", "try_9b", "profile"),
    [
        (80, False, "qwen35_9b_a100"),
        (40, False, "qwen35_9b_a100"),
        (22.5, False, "qwen35_4b_l4"),
        (22.5, True, "qwen35_9b_l4"),
        (16, True, "qwen35_4b_l4"),
        (15, False, "qwen35_2b_small"),
    ],
)
def test_profile_follows_gpu_memory(vram, try_9b, profile):
    assert pick_profile(vram, try_9b=try_9b) == profile


def test_every_profile_trains_bf16_lora_and_the_9b_l4_ladder_steps_down():
    for key in ("qwen35_2b_small", "qwen35_4b_l4", "qwen35_9b_l4", "qwen35_9b_a100"):
        assert load_config(key).model_id.startswith("unsloth/Qwen3.5-")
    ladder = fallback_ladder(load_config("qwen35_9b_l4"))
    steps = [(c.key, c.max_image_side, c.lora.r) for c in ladder]
    assert steps[:4] == [
        ("qwen35_9b_l4", 672, 16),
        ("qwen35_9b_l4", 480, 16),
        ("qwen35_9b_l4", 480, 8),
        ("qwen35_4b_l4", 896, 16),
    ]
    assert steps[-1][0] == "qwen35_2b_small"
    assert load_config("qwen35_9b_l4").effective_batch == 8


def test_a_diagonal_crack_mask_becomes_one_line_from_corner_to_corner():
    mask = np.zeros((100, 100), dtype=bool)
    for i in range(100):
        mask[i, max(0, i - 1) : i + 2] = True
    [line] = lines_from_mask(mask)
    (x0, y0), (x1, y1) = sorted([line[0], line[-1]])
    assert x0 < 0.1 and y0 < 0.1 and x1 > 0.9 and y1 > 0.9


def test_folder_names_give_public_labels():
    sdnet = next(s for s in SOURCES if s.key == "sdnet2018")
    kasbah = next(s for s in SOURCES if s.key == "kasbah_algiers")
    assert labels_for(sdnet, Path("W/CW/7001-1.jpg")) == ("crack",)
    assert labels_for(sdnet, Path("D/UD/7001-2.jpg")) == ()
    assert labels_for(kasbah, Path("train/Efflorescence/a.jpg")) == ("salt_efflorescence",)
    assert labels_for(kasbah, Path("readme/a.jpg")) is None


def test_bridge_turns_elements_into_http_detector_boxes():
    found = detections(parse_answer(wall_map_target([CRACK, LOSS])))["detections"]
    crack, loss = found
    assert crack["label"] == "crack" and crack["severity"] == "moderate" and crack["score"] == 0.9
    assert crack["box"] == [0.085, 0.1, 0.115, 0.4]
    assert loss["box"] == [0.5, 0.5, 1.0, 1.0] and loss["score"] == 0.6


def test_bridge_output_fits_the_backend_http_detector():
    payload = detections(parse_answer(wall_map_target([CRACK, LOSS])))
    parsed = parse_detections(payload, LabelMap({}), 800, 400)
    assert [(d.damage_type.value, d.severity.value) for d in parsed] == [
        ("crack", "moderate"),
        ("plaster_loss", "watch"),
    ]
