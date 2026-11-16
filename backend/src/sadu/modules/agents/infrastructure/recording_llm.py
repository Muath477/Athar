"""Wraps the LLM port to log every call's cost and to stop live calls past the daily budget."""

import time
from contextvars import ContextVar
from uuid import UUID

import structlog

from sadu.modules.admin import api as admin
from sadu.shared.db import unit_of_work
from sadu.shared.ports.llm import LLMPort, LLMRefused, LLMUnavailable, StructuredRequest, StructuredResult

log = structlog.get_logger()

current_observation: ContextVar[UUID | None] = ContextVar("current_observation", default=None)


class RecordingLLM:
    def __init__(self, inner: LLMPort, daily_budget_usd: float) -> None:
        self._inner = inner
        self._budget = daily_budget_usd

    async def complete_structured(self, request: StructuredRequest) -> StructuredResult:
        async with unit_of_work() as session:
            if await admin.spent_today_usd(session) >= self._budget:
                log.warning("llm_budget_exhausted", agent=request.agent)
                raise LLMUnavailable("daily budget reached")
        started = time.monotonic()
        try:
            result = await self._inner.complete_structured(request)
        except (LLMUnavailable, LLMRefused) as error:
            failed = StructuredResult({}, "", 0, 0, 0.0, int((time.monotonic() - started) * 1000))
            await _record(request.agent, failed, "refused" if isinstance(error, LLMRefused) else "failed")
            raise
        await _record(request.agent, result, "ok")
        return result


async def _record(agent: str, result: StructuredResult, status: str) -> None:
    async with unit_of_work() as session:
        await admin.record_llm_call(
            session,
            observation_id=current_observation.get(),
            agent=agent,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
            status=status,
        )
