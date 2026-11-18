from collections.abc import AsyncIterator, Sequence
from typing import TypedDict

import structlog
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from sadu.modules.assistant.application.context import ToolOutcome, TurnContext
from sadu.modules.assistant.application.events import (
    AGENT_EVENTS,
    AgentEvent,
    Replied,
    SkillChosen,
    Thinking,
    ToolFinished,
    ToolStarted,
)
from sadu.modules.assistant.application.prompts import (
    ROUTER_SYSTEM,
    planner_system,
    planner_text,
    router_schema,
    router_text,
)
from sadu.modules.assistant.application.tools import Toolbox
from sadu.modules.assistant.domain.decision import ToolCall, decision_schema, parse_decision
from sadu.modules.assistant.domain.skills import Skill, route_by_keywords
from sadu.shared.ports.llm import LLMPort, LLMRefused, LLMUnavailable, ModelRole, StructuredRequest

log = structlog.get_logger()

MAX_TOOL_STEPS = 6
PLANNER_TIMEOUT_S = 30.0
LLM_DOWN_REPLY = (
    "المساعد غير متاح الآن: الخدمة متوقفة أو بلغت ميزانية اليوم حدها. "
    "ما زال بإمكانك تحليل الصور المرفقة بزر «حلّل الصورة»، وستُحفظ النتائج في المحادثة."
)
CONFUSED_REPLY = "لم أستطع إكمال الطلب بهذه الصيغة. وضّح ما تريد فحصه أو أرفق الصورة وأعد المحاولة."
STEP_LIMIT_REPLY = "توقفت بعد عدد الخطوات المسموح به في الرد الواحد. هذه نتائج ما أنجزته:"


class TurnState(TypedDict, total=False):
    context: TurnContext
    skill: str
    llm_down: bool
    steps: int
    call: ToolCall | None
    outcomes: list[ToolOutcome]


class Agent:
    def __init__(self, llm: LLMPort, skills: Sequence[Skill], toolbox: Toolbox) -> None:
        if not skills:
            raise ValueError("The assistant needs at least one skill")
        self._llm = llm
        self._skills = {skill.name: skill for skill in skills}
        self._toolbox = toolbox
        self._graph = self._build().compile()

    @property
    def skills(self) -> tuple[Skill, ...]:
        return tuple(self._skills.values())

    async def run(self, context: TurnContext) -> AsyncIterator[AgentEvent]:
        start: TurnState = {"context": context, "steps": 0, "outcomes": [], "call": None}
        async for event in self._graph.astream(start, stream_mode="custom"):
            if isinstance(event, AGENT_EVENTS):
                yield event

    def _build(self) -> StateGraph[TurnState]:
        graph = StateGraph(TurnState)
        graph.add_node("route", self._route)
        graph.add_node("think", self._think)
        graph.add_node("act", self._act)
        graph.add_edge(START, "route")
        graph.add_edge("route", "think")
        graph.add_conditional_edges("think", _after_think, ["act", END])
        graph.add_edge("act", "think")
        return graph

    async def _route(self, state: TurnState) -> TurnState:
        context = state["context"]
        skills = self.skills
        llm_down = False
        chosen = None
        try:
            result = await self._llm.complete_structured(
                StructuredRequest(
                    agent="assistant_router",
                    role=ModelRole.FAST,
                    system=ROUTER_SYSTEM,
                    text=router_text(context, skills),
                    schema=router_schema(skills),
                )
            )
            chosen = self._skills.get(str(result.data.get("skill")))
        except LLMUnavailable as error:
            log.info("assistant_router_unavailable", error=str(error))
            llm_down = True
        except LLMRefused:
            log.info("assistant_router_refused")
        skill = chosen or route_by_keywords(skills, context.message, context.latest_kinds)
        get_stream_writer()(SkillChosen(skill.name, skill.title_ar))
        return {"skill": skill.name, "llm_down": llm_down}

    async def _think(self, state: TurnState) -> TurnState:
        write = get_stream_writer()
        skill = self._skills[state["skill"]]
        outcomes = state["outcomes"]
        if state.get("llm_down"):
            write(Replied(_with_outcomes(LLM_DOWN_REPLY, outcomes), skill.name, llm_available=False))
            return {"call": None}
        if state["steps"] >= MAX_TOOL_STEPS:
            write(Replied(_with_outcomes(STEP_LIMIT_REPLY, outcomes), skill.name))
            return {"call": None}

        write(Thinking(state["steps"] + 1))
        request = StructuredRequest(
            agent="assistant_planner",
            role=ModelRole.MAIN,
            system=planner_system(skill),
            text=planner_text(state["context"], skill, outcomes),
            schema=decision_schema(skill.tools),
            timeout_s=PLANNER_TIMEOUT_S,
        )
        try:
            decision = parse_decision((await self._llm.complete_structured(request)).data, skill.tools)
        except LLMUnavailable as error:
            log.info("assistant_planner_unavailable", error=str(error))
            write(Replied(_with_outcomes(LLM_DOWN_REPLY, outcomes), skill.name, llm_available=False))
            return {"call": None}
        except (LLMRefused, ValueError) as error:
            log.info("assistant_planner_unusable", error=str(error))
            write(Replied(_with_outcomes(CONFUSED_REPLY, outcomes), skill.name))
            return {"call": None}

        if decision.call is None:
            write(Replied(decision.reply_ar, skill.name))
        return {"call": decision.call}

    async def _act(self, state: TurnState) -> TurnState:
        call = state["call"]
        if call is None:
            raise RuntimeError("act reached without a tool call")
        write = get_stream_writer()
        write(ToolStarted(call.tool))
        outcome = await self._toolbox.run(call, state["context"], state["outcomes"])
        write(ToolFinished(outcome))
        return {"outcomes": [*state["outcomes"], outcome], "steps": state["steps"] + 1, "call": None}


def _after_think(state: TurnState) -> str:
    return "act" if state.get("call") is not None else END


def _with_outcomes(message: str, outcomes: Sequence[ToolOutcome]) -> str:
    if not outcomes:
        return message
    return "\n".join([message, *(f"- {o.summary_ar}" for o in outcomes)])
