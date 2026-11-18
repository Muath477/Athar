from uuid import uuid4

import pytest

from sadu.modules.assistant.application.agent import LLM_DOWN_REPLY, MAX_TOOL_STEPS, Agent
from sadu.modules.assistant.application.context import AttachmentRef, ToolOutcome, TurnContext
from sadu.modules.assistant.application.events import (
    Replied,
    SkillChosen,
    Thinking,
    ToolFinished,
    ToolStarted,
)
from sadu.modules.assistant.application.tools import Toolbox
from sadu.modules.assistant.domain.conversation import (
    ActionAlreadySettled,
    ActionStatus,
    AttachmentKind,
    safe_file_name,
    settle,
    title_from,
)
from sadu.modules.assistant.domain.decision import ToolName, decision_schema, parse_decision
from sadu.modules.assistant.infrastructure.skill_files import load_skills
from tests.fakes import FakeLLM

pytestmark = pytest.mark.anyio

SKILLS = load_skills()


def test_a_pending_send_is_confirmed_or_cancelled_exactly_once():
    assert settle(ActionStatus.PENDING, confirm=True) is ActionStatus.CONFIRMED
    assert settle(ActionStatus.PENDING, confirm=False) is ActionStatus.CANCELLED
    for decided in (ActionStatus.CONFIRMED, ActionStatus.CANCELLED):
        with pytest.raises(ActionAlreadySettled):
            settle(decided, confirm=True)


def test_decisions_keep_known_arguments_and_reject_tools_outside_the_skill():
    allowed = (ToolName.ANALYSE_PHOTO, ToolName.LIST_SITES)
    decision = parse_decision(
        {
            "action": "call_tool",
            "tool": "analyse_photo",
            "arguments": {"attachment_id": "a", "facade_id": None, "approve": "yes"},
            "reply_ar": "",
        },
        allowed,
    )
    assert decision.call is not None and decision.call.arguments == {"attachment_id": "a"}
    assert parse_decision({"action": "reply", "reply_ar": " تم "}, allowed).reply_ar == "تم"
    with pytest.raises(ValueError, match="not allowed"):
        parse_decision({"action": "call_tool", "tool": "send_report", "arguments": {}}, allowed)
    with pytest.raises(ValueError, match="Unknown tool"):
        parse_decision({"action": "call_tool", "tool": "approve_map", "arguments": {}}, allowed)
    with pytest.raises(ValueError, match="reply_ar"):
        parse_decision({"action": "reply", "reply_ar": ""}, allowed)
    assert decision_schema(allowed)["properties"]["tool"]["enum"] == ["analyse_photo", "list_sites", None]


def test_file_names_and_titles_are_cleaned():
    assert safe_file_name("../../etc/passwd", "x") == "passwd"
    assert safe_file_name("C:\\photos\\جدار\x00.jpg", "x") == "جدار.jpg"
    assert safe_file_name("   ", "صورة.jpg") == "صورة.jpg"
    assert title_from("  حلّل   الصورة ", "جديد") == "حلّل الصورة"
    assert title_from("", "جديد") == "جديد"
    assert len(title_from("كلمة " * 40, "جديد")) == 60


class StubToolbox(Toolbox):
    def __init__(self) -> None:
        self.calls: list[ToolName] = []

    async def run(self, call, context, earlier):
        self.calls.append(call.tool)
        return ToolOutcome(call.tool, True, f"نفذت {call.tool}", {"step": len(earlier)})


def context(message: str = "حلّل الصورة") -> TurnContext:
    photo = AttachmentRef(uuid4(), AttachmentKind.PHOTO, "w.jpg", "k")
    return TurnContext(uuid4(), uuid4(), None, message, (photo,), (photo.id,), ())


async def collect(agent: Agent, turn: TurnContext) -> list:
    return [event async for event in agent.run(turn)]


async def test_when_the_model_is_down_the_router_falls_back_and_the_reply_says_so():
    toolbox = StubToolbox()
    events = await collect(Agent(FakeLLM(), SKILLS, toolbox), context())
    assert events == [
        SkillChosen("wall-photo-inspection", "فحص صورة جدار"),
        Replied(LLM_DOWN_REPLY, "wall-photo-inspection", llm_available=False),
    ]
    assert toolbox.calls == []


async def test_the_planner_loops_through_tools_until_it_replies():
    def responder(request):
        if request.agent == "assistant_router":
            return {"skill": "wall-photo-inspection"}
        if '"this_turn": []' in request.text:
            return {"action": "call_tool", "tool": "list_sites", "arguments": {}, "reply_ar": ""}
        return {"action": "reply", "tool": None, "arguments": {}, "reply_ar": "انتهيت."}

    toolbox = StubToolbox()
    events = await collect(Agent(FakeLLM(responder), SKILLS, toolbox), context())
    assert [type(e) for e in events] == [SkillChosen, Thinking, ToolStarted, ToolFinished, Thinking, Replied]
    assert events[-1] == Replied("انتهيت.", "wall-photo-inspection")


async def test_a_planner_that_never_stops_is_cut_off_after_the_step_limit():
    def responder(request):
        if request.agent == "assistant_router":
            return {"skill": "treatment-check"}
        return {"action": "call_tool", "tool": "find_treatments", "arguments": {}, "reply_ar": ""}

    toolbox = StubToolbox()
    events = await collect(Agent(FakeLLM(responder), SKILLS, toolbox), context("ما المعالجة؟"))
    assert len(toolbox.calls) == MAX_TOOL_STEPS
    assert isinstance(events[-1], Replied) and events[-1].text.count("- نفذت") == MAX_TOOL_STEPS


async def test_a_tool_outside_the_chosen_skill_ends_the_turn_without_running():
    def responder(request):
        if request.agent == "assistant_router":
            return {"skill": "treatment-check"}
        return {"action": "call_tool", "tool": "send_report", "arguments": {}, "reply_ar": ""}

    toolbox = StubToolbox()
    events = await collect(Agent(FakeLLM(responder), SKILLS, toolbox), context("ما المعالجة؟"))
    assert toolbox.calls == [] and isinstance(events[-1], Replied) and events[-1].llm_available
