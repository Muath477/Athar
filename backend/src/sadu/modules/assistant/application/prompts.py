import json
from collections.abc import Sequence
from typing import Any

from sadu.modules.assistant.application.context import HistoryEntry, ToolOutcome, TurnContext
from sadu.modules.assistant.domain.skills import Skill

HISTORY_IN_PROMPT = 12
ELEMENTS_IN_PROMPT = 30

ROUTER_SYSTEM = """You route a message from heritage-site staff to one inspection skill.
Pick the skill whose purpose matches the message and its attachments. Return its name."""

PLANNER_SYSTEM = """You are the Athar inspection assistant for staff who look after mud-brick heritage walls.
Follow the skill below step by step. At each step either call exactly one tool or reply to the user.
Rules you never break:
- You never approve maps or treatments. Everything you produce is a draft for a restoration specialist.
- send_report only prepares a request; the user confirms it with a button. Never say a report was sent.
- Use only facts returned by tools or written by the user. When unsure, say so and ask for a field visit.
- Ids you pass to tools must come from the attachments, the history or earlier tool results.
- Reply in clear Modern Standard Arabic, short and specific.

Skill:
"""


def router_text(context: TurnContext, skills: Sequence[Skill]) -> str:
    return json.dumps(
        {
            "message": context.message,
            "attachment_kinds": sorted(context.latest_kinds),
            "skills": [{"name": s.name, "when": s.when_ar} for s in skills],
        },
        ensure_ascii=False,
    )


def router_schema(skills: Sequence[Skill]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["skill"],
        "properties": {"skill": {"type": "string", "enum": [s.name for s in skills]}},
    }


def planner_system(skill: Skill) -> str:
    return f"{PLANNER_SYSTEM}{skill.body}"


def planner_text(context: TurnContext, skill: Skill, outcomes: Sequence[ToolOutcome]) -> str:
    return json.dumps(
        {
            "skill": skill.name,
            "message": context.message,
            "new_attachment_ids": [str(i) for i in context.latest_attachment_ids],
            "attachments": [
                {"id": str(a.id), "kind": a.kind.value, "file_name": a.file_name} for a in context.attachments
            ],
            "history": [_history_entry(e) for e in context.history[-HISTORY_IN_PROMPT:]],
            "this_turn": [
                {"tool": o.tool.value, "ok": o.ok, "summary_ar": o.summary_ar, "data": _trimmed(o.data)}
                for o in outcomes
            ],
        },
        ensure_ascii=False,
    )


def _history_entry(entry: HistoryEntry) -> dict[str, Any]:
    item: dict[str, Any] = {"role": entry.role.value, "text": entry.text}
    if entry.tool is not None:
        item["tool"] = entry.tool.value
        item["ok"] = entry.ok
        item["ids"] = {key: value for key, value in entry.data.items() if key.endswith("_id") and value}
    return item


def _trimmed(data: dict[str, Any]) -> dict[str, Any]:
    elements = data.get("elements")
    if isinstance(elements, list) and len(elements) > ELEMENTS_IN_PROMPT:
        return {**data, "elements": elements[:ELEMENTS_IN_PROMPT], "elements_total": len(elements)}
    return data
