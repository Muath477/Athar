import json
from collections.abc import Sequence
from typing import Any

from sadu.modules.assistant.domain.arabic_text import normalize_ar
from sadu.modules.assistant.domain.conversation import AttachmentKind
from sadu.modules.assistant.domain.decision import ARGUMENT_NAMES, LIST_ARGUMENT_NAMES, ToolName
from sadu.modules.assistant.domain.skills import Skill, route_by_keywords
from sadu.shared.ports.llm import LLMUnavailable, StructuredRequest, StructuredResult

PHOTO_SKILLS = {"wall-photo-inspection", "drone-roof-and-wall-head"}
REPORT_WORDS = ("تقرير", "تدقيق", "ملف")
SEND_WORDS = ("ارسل", "ارسال", "ابعث")
FACADE_WORDS = ("واجهه", "جدار")
DRAFT_NOTE = "كل ما سبق مسودة تنتظر مراجعة المختص، ولا يُعتمد شيء دون موافقته."
CONFIRM_NOTE = "اضغط «أكّد الإرسال» ليصل الملف إلى المختصين، أو «ألغِ الإرسال»."


class ScriptedPlanner:
    def __init__(self, skills: Sequence[Skill]) -> None:
        self._skills = tuple(skills)

    async def complete_structured(self, request: StructuredRequest) -> StructuredResult:
        prompt = json.loads(request.text)
        if request.agent == "assistant_router":
            data = self._route(prompt)
        elif request.agent == "assistant_planner":
            data = _plan(prompt)
        else:
            raise LLMUnavailable(f"{request.agent}: the scripted planner only serves the assistant")
        return StructuredResult(data, "scripted", 0, 0, 0.0, 0)

    def _route(self, prompt: dict[str, Any]) -> dict[str, Any]:
        kinds = [AttachmentKind(kind) for kind in prompt["attachment_kinds"]]
        return {"skill": route_by_keywords(self._skills, prompt["message"], kinds).name}


def _plan(prompt: dict[str, Any]) -> dict[str, Any]:
    message = normalize_ar(prompt["message"])
    done = prompt["this_turn"]
    called = [step["tool"] for step in done]
    sites = next((step["data"]["sites"] for step in done if step["tool"] == ToolName.LIST_SITES), None)
    skill = prompt["skill"]

    if skill in PHOTO_SKILLS:
        photos = [
            a["id"]
            for a in prompt["attachments"]
            if a["id"] in prompt["new_attachment_ids"] and a["kind"] == AttachmentKind.PHOTO
        ]
        waiting = photos[called.count(ToolName.ANALYSE_PHOTO) :]
        if waiting:
            if sites is None and any(word in message for word in FACADE_WORDS):
                return _call(ToolName.LIST_SITES)
            return _call(
                ToolName.ANALYSE_PHOTO, attachment_id=waiting[0], facade_id=_facade_in(message, sites)
            )

    if skill == "satellite-alert-review" and ToolName.GET_WATCH_STATUS not in called:
        if sites is None:
            return _call(ToolName.LIST_SITES)
        site_id = _site_in(message, sites)
        if site_id is not None:
            return _call(ToolName.GET_WATCH_STATUS, site_id=site_id)

    if skill == "treatment-check" and ToolName.FIND_TREATMENTS not in called:
        return _call(ToolName.FIND_TREATMENTS)

    wants_send = any(word in message for word in SEND_WORDS)
    wants_report = wants_send or skill == "audit-report" or any(word in message for word in REPORT_WORDS)
    reuse_report = wants_send and _has_report(prompt) and ToolName.ANALYSE_PHOTO not in called
    if wants_report and ToolName.DRAFT_AUDIT_REPORT not in called and not reuse_report:
        return _call(ToolName.DRAFT_AUDIT_REPORT)
    if wants_send and ToolName.SEND_REPORT not in called:
        return _call(ToolName.SEND_REPORT)
    return _reply(done)


def _call(tool: ToolName, **arguments: str | None) -> dict[str, Any]:
    return {
        "action": "call_tool",
        "tool": tool.value,
        "arguments": _no_arguments() | arguments,
        "reply_ar": "",
    }


def _reply(done: Sequence[dict[str, Any]]) -> dict[str, Any]:
    lines = [step["summary_ar"] for step in done] or ["لم أحتج إلى أداة لهذا الطلب."]
    text = "\n".join(f"- {line}" for line in lines)
    note = CONFIRM_NOTE if any(step["tool"] == ToolName.SEND_REPORT and step["ok"] for step in done) else ""
    reply = "\n".join(part for part in (text, note, DRAFT_NOTE) if part)
    return {"action": "reply", "tool": None, "arguments": _no_arguments(), "reply_ar": reply}


def _no_arguments() -> dict[str, Any]:
    return dict.fromkeys((*ARGUMENT_NAMES, *LIST_ARGUMENT_NAMES))


def _has_report(prompt: dict[str, Any]) -> bool:
    return any(a["kind"] == AttachmentKind.AUDIT_REPORT for a in prompt["attachments"])


def _facade_in(message: str, sites: list[dict[str, Any]] | None) -> str | None:
    for site in sites or []:
        for facade in site["facades"]:
            if normalize_ar(facade["name_ar"]) in message:
                return str(facade["id"])
    return None


def _site_in(message: str, sites: list[dict[str, Any]]) -> str | None:
    return next((str(s["id"]) for s in sites if normalize_ar(s["name_ar"]) in message), None)
