from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class ModelRole(StrEnum):
    """Which model tier a call needs; the adapter maps roles to concrete model IDs."""

    MAIN = "main"
    FAST = "fast"


@dataclass(frozen=True)
class ImageInput:
    data: bytes
    media_type: str = "image/jpeg"
    caption: str = ""


@dataclass(frozen=True)
class StructuredRequest:
    agent: str
    role: ModelRole
    system: str
    text: str
    schema: dict[str, Any]
    images: tuple[ImageInput, ...] = ()
    effort: str = "low"
    timeout_s: float = 8.0
    max_tokens: int = 4000


@dataclass(frozen=True)
class StructuredResult:
    data: dict[str, Any]
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int


class LLMRefused(Exception):
    """The model declined; callers route the case to a human instead of retrying."""


class LLMUnavailable(Exception):
    pass


class LLMPort(Protocol):
    async def complete_structured(self, request: StructuredRequest) -> StructuredResult: ...
