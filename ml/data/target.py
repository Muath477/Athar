import json
from enum import StrEnum
from typing import Any

from sadu.modules.mapping.application.element_prompt import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    USER_TEXT,
    elements_answer,
)
from sadu.modules.mapping.domain.elements import Element, element_from_json

PATCH_SYSTEM_PROMPT = """You inspect close-up photos of wall surfaces (earthen plaster, brick, stone or
concrete) for a conservation team. Answer with JSON only."""
PATCH_TAGS_TEXT = (
    'List the damage types visible in this close-up as {"damage_types": [...]}, using only '
    "crack, plaster_loss and salt_efflorescence, and an empty list for a sound surface."
)
CRACK_LINES_TEXT = (
    'Trace every crack in this close-up as {"elements": [{"damage_type": "crack", "geometry": "line", '
    '"points": [[x, y], ...]}]} with x and y as fractions of the photo.'
)


class Task(StrEnum):
    WALL_MAP = "wall_map"
    PATCH_TAGS = "patch_tags"
    CRACK_LINES = "crack_lines"


def compact(answer: dict[str, Any]) -> str:
    return json.dumps(answer, ensure_ascii=False, separators=(",", ":"))


def wall_map_target(elements: list[dict[str, Any]]) -> str:
    parsed: list[Element] = [element_from_json(item) for item in elements]
    return compact(elements_answer(parsed))


def patch_tags_target(damage_types: list[str]) -> str:
    return compact({"damage_types": sorted(set(damage_types))})


def crack_lines_target(lines: list[list[tuple[float, float]]]) -> str:
    elements = [
        {"damage_type": "crack", "geometry": "line", "points": [[round(x, 3), round(y, 3)] for x, y in line]}
        for line in lines
    ]
    return compact({"elements": elements})


def chat(task: Task, image: str, target: str) -> list[dict[str, Any]]:
    system, text = _prompts(task)
    return [
        {"role": "system", "content": [{"type": "text", "text": system}]},
        {"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": text}]},
        {"role": "assistant", "content": [{"type": "text", "text": target}]},
    ]


def _prompts(task: Task) -> tuple[str, str]:
    if task is Task.WALL_MAP:
        return SYSTEM_PROMPT, USER_TEXT
    if task is Task.PATCH_TAGS:
        return PATCH_SYSTEM_PROMPT, PATCH_TAGS_TEXT
    return PATCH_SYSTEM_PROMPT, CRACK_LINES_TEXT


__all__ = ["PROMPT_VERSION"]
