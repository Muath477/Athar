"""Orchestrator: the fast model proposes a plan; the domain invariants decide whether it stands."""

import json
from typing import Any

import structlog

from sadu.modules.agents.domain.planning import ObservationContext, Step, accept_plan
from sadu.shared.ports.llm import LLMPort, LLMRefused, LLMUnavailable, ModelRole, StructuredRequest

log = structlog.get_logger()

SYSTEM_PROMPT = """You plan how to process one visitor photo of a heritage site.
Available steps, in this order only: identify (which facade), monitor (compare with the baseline
for damage), verify (check monitoring results), guide (tell the visitor the verified story).
Always end with guide. Monitor needs identify before it and verify after it, and is allowed only
when the site is known and the visitor shared location or came on a mission.
Return the steps you choose."""

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["steps"],
    "properties": {"steps": {"type": "array", "items": {"type": "string", "enum": [s.value for s in Step]}}},
}


async def plan_steps(
    llm: LLMPort, context: ObservationContext, *, has_heading: bool, facade_count: int
) -> tuple[Step, ...]:
    request = StructuredRequest(
        agent="orchestrator",
        role=ModelRole.FAST,
        system=SYSTEM_PROMPT,
        text=json.dumps(
            {
                "has_location": context.has_location,
                "has_heading": has_heading,
                "on_mission": context.on_mission,
                "site_known": context.has_site,
                "facade_count": facade_count,
            }
        ),
        schema=PLAN_SCHEMA,
    )
    try:
        proposed = (await llm.complete_structured(request)).data["steps"]
    except (LLMUnavailable, LLMRefused) as error:
        log.info("plan_fallback", error=str(error))
        proposed = []
    return accept_plan(proposed, context)
