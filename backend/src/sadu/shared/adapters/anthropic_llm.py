"""LLMPort adapter for the Claude API (ADR-003)."""

import base64
import json
import time
from typing import Any

import anthropic

from sadu.shared.config import Settings
from sadu.shared.ports.llm import (
    LLMRefused,
    LLMUnavailable,
    ModelRole,
    StructuredRequest,
    StructuredResult,
)
from sadu.shared.resilience import call_with_policy

# USD per million tokens (input, output), Anthropic first-party rates as of 2026-11-03.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
SERVER_SIDE_FALLBACK_BETA = "server-side-fallback-2026-07-01"
MODELS_WITH_FALLBACK = {"claude-sonnet-5-5"}


class AnthropicLLM:
    def __init__(self, settings: Settings) -> None:
        api_key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
        self._client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=2)
        self._models = {ModelRole.MAIN: settings.sadu_model_main, ModelRole.FAST: settings.sadu_model_fast}

    async def complete_structured(self, request: StructuredRequest) -> StructuredResult:
        model = self._models[request.role]
        started = time.monotonic()
        try:
            response = await call_with_policy(
                f"llm.{request.agent}",
                lambda: self._send(model, request),
                timeout_s=request.timeout_s,
            )
        except anthropic.APIError as error:
            raise LLMUnavailable(f"{request.agent}: {type(error).__name__}") from error
        except TimeoutError as error:
            raise LLMUnavailable(f"{request.agent}: timeout") from error

        if response.stop_reason == "refusal":
            raise LLMRefused(request.agent)
        text = next((block.text for block in response.content if block.type == "text"), None)
        if text is None:
            raise LLMUnavailable(f"{request.agent}: no text block (stop_reason={response.stop_reason})")

        input_tokens, output_tokens = response.usage.input_tokens, response.usage.output_tokens
        return StructuredResult(
            data=json.loads(text),
            model=response.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=estimate_cost(response.model, input_tokens, output_tokens),
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    async def _send(self, model: str, request: StructuredRequest) -> Any:
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": _content_blocks(request)}],
            "output_config": {
                "effort": request.effort,
                "format": {"type": "json_schema", "schema": request.schema},
            },
        }
        if model in MODELS_WITH_FALLBACK:
            return await self._client.beta.messages.create(
                **params, betas=[SERVER_SIDE_FALLBACK_BETA], fallbacks="default"
            )
        return await self._client.messages.create(**params)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = PRICES_PER_MTOK.get(model, PRICES_PER_MTOK["claude-sonnet-5-5"])
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


def _content_blocks(request: StructuredRequest) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for image in request.images:
        if image.caption:
            blocks.append({"type": "text", "text": image.caption})
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image.media_type,
                    "data": base64.standard_b64encode(image.data).decode("ascii"),
                },
            }
        )
    blocks.append({"type": "text", "text": request.text})
    return blocks
