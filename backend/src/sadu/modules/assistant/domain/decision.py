from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

MAX_REPLY_CHARS = 4000
ARGUMENT_NAMES = (
    "attachment_id",
    "site_id",
    "facade_id",
    "map_id",
    "damage_type",
    "severity",
    "title_ar",
    "summary_ar",
    "note_ar",
)
LIST_ARGUMENT_NAMES = ("recommendations_ar",)
KNOWN_ARGUMENTS = frozenset((*ARGUMENT_NAMES, *LIST_ARGUMENT_NAMES))


class ToolName(StrEnum):
    ANALYSE_PHOTO = "analyse_photo"
    GET_SITE_CONDITION = "get_site_condition"
    LIST_SITES = "list_sites"
    GET_MAP = "get_map"
    GET_WATCH_STATUS = "get_watch_status"
    FIND_TREATMENTS = "find_treatments"
    DRAFT_AUDIT_REPORT = "draft_audit_report"
    SEND_REPORT = "send_report"


@dataclass(frozen=True)
class ToolCall:
    tool: ToolName
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Decision:
    reply_ar: str
    call: ToolCall | None = None


def decision_schema(tools: Sequence[ToolName]) -> dict[str, Any]:
    nullable_text = {"type": ["string", "null"]}
    arguments = {name: nullable_text for name in ARGUMENT_NAMES} | {
        name: {"type": ["array", "null"], "items": {"type": "string"}} for name in LIST_ARGUMENT_NAMES
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["action", "tool", "arguments", "reply_ar"],
        "properties": {
            "action": {"type": "string", "enum": ["call_tool", "reply"]},
            "tool": {"type": ["string", "null"], "enum": [*(t.value for t in tools), None]},
            "arguments": {
                "type": "object",
                "additionalProperties": False,
                "required": list(arguments),
                "properties": arguments,
            },
            "reply_ar": {"type": "string"},
        },
    }


def parse_decision(data: dict[str, Any], allowed: Sequence[ToolName]) -> Decision:
    reply = str(data.get("reply_ar") or "").strip()[:MAX_REPLY_CHARS]
    if data.get("action") != "call_tool":
        if not reply:
            raise ValueError("A reply decision needs reply_ar")
        return Decision(reply)
    try:
        tool = ToolName(str(data.get("tool")))
    except ValueError as error:
        raise ValueError(f"Unknown tool {data.get('tool')!r}") from error
    if tool not in allowed:
        raise ValueError(f"Tool {tool} is not allowed in this skill")
    raw = data.get("arguments") or {}
    arguments = {key: value for key, value in raw.items() if key in KNOWN_ARGUMENTS and value is not None}
    return Decision(reply, ToolCall(tool, arguments))
