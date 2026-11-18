import base64
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from sadu.modules.mapping.application.element_prompt import (
    ELEMENTS_SCHEMA,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    USER_TEXT,
    InvalidAnswer,
    parse_elements,
)
from sadu.modules.mapping.application.ports import (
    ActiveModelLookup,
    DetectionInput,
    DetectionOutput,
    DetectorUnavailable,
    ModelChoice,
)
from sadu.modules.mapping.domain.elements import Element
from sadu.modules.mapping.domain.raster import cells_from_elements
from sadu.shared.resilience import call_with_policy

UNREGISTERED_VERSION = "unregistered"
MAX_ANSWER_TOKENS = 4096
REPAIR_TEXT = (
    "That answer could not be used: {error}. Reply again with the corrected JSON only, "
    'in the form {{"elements": [...]}}.'
)
_THINKING = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


@dataclass(frozen=True)
class QwenEndpoint:
    url: str
    model: str
    timeout_s: float
    token: str | None = None
    json_schema: bool = True

    @property
    def completions_url(self) -> str:
        base = self.url.rstrip("/")
        return base if base.endswith("/chat/completions") else f"{base}/chat/completions"


class QwenVisionDetector:
    def __init__(
        self,
        endpoint: QwenEndpoint,
        active_model: ActiveModelLookup | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._active_model = active_model
        self._transport = transport

    @property
    def name(self) -> str:
        return "qwen"

    async def detect(self, request: DetectionInput) -> DetectionOutput:
        choice = await self._model()
        messages = _messages(request.rectified_jpeg)
        async with httpx.AsyncClient(transport=self._transport) as http:
            answer = await self._complete(http, choice.name, messages)
            try:
                elements = parse_answer(answer)
            except InvalidAnswer as error:
                retry = [
                    *messages,
                    {"role": "assistant", "content": answer},
                    {"role": "user", "content": REPAIR_TEXT.format(error=error)},
                ]
                elements = await self._repaired(http, choice.name, retry)
        return DetectionOutput(
            cells=cells_from_elements(elements, request.grid),
            elements=elements,
            model=f"{choice.name}@{choice.version}",
            prompt_version=PROMPT_VERSION,
        )

    async def _model(self) -> ModelChoice:
        active = await self._active_model() if self._active_model else None
        return active or ModelChoice(self._endpoint.model, UNREGISTERED_VERSION)

    async def _repaired(
        self, http: httpx.AsyncClient, model: str, messages: list[dict[str, Any]]
    ) -> tuple[Element, ...]:
        answer = await self._complete(http, model, messages)
        try:
            return parse_answer(answer)
        except InvalidAnswer as error:
            raise DetectorUnavailable(f"damage model answer invalid after a repair: {error}") from error

    async def _complete(self, http: httpx.AsyncClient, model: str, messages: list[dict[str, Any]]) -> str:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": MAX_ANSWER_TOKENS,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if self._endpoint.json_schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "wall_elements", "schema": ELEMENTS_SCHEMA},
            }
        headers = {"Authorization": f"Bearer {self._endpoint.token}"} if self._endpoint.token else {}

        async def send() -> str:
            response = await http.post(
                self._endpoint.completions_url, json=body, headers=headers, timeout=self._endpoint.timeout_s
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])

        try:
            return await call_with_policy("qwen_detector", send, timeout_s=self._endpoint.timeout_s)
        except (httpx.HTTPError, TimeoutError, ValueError, KeyError, IndexError, TypeError) as error:
            raise DetectorUnavailable(f"damage model call failed: {type(error).__name__}") from error


def parse_answer(answer: str) -> tuple[Element, ...]:
    text = _FENCE.sub("", _THINKING.sub("", answer).strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise InvalidAnswer(f"not valid JSON ({error.msg})") from error
    return parse_elements(data)


def _messages(jpeg: bytes) -> list[dict[str, Any]]:
    image_url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": USER_TEXT},
            ],
        },
    ]
