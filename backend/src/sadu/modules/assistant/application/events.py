from dataclasses import dataclass

from sadu.modules.assistant.application.context import ToolOutcome
from sadu.modules.assistant.domain.decision import ToolName


@dataclass(frozen=True)
class SkillChosen:
    name: str
    title_ar: str


@dataclass(frozen=True)
class Thinking:
    step: int


@dataclass(frozen=True)
class ToolStarted:
    tool: ToolName


@dataclass(frozen=True)
class ToolFinished:
    outcome: ToolOutcome


@dataclass(frozen=True)
class Replied:
    text: str
    skill: str
    llm_available: bool = True


type AgentEvent = SkillChosen | Thinking | ToolStarted | ToolFinished | Replied

AGENT_EVENTS = (SkillChosen, Thinking, ToolStarted, ToolFinished, Replied)
