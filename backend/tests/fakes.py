"""Test doubles for the outbound ports."""

from collections.abc import Callable
from typing import Any

from sadu.shared.ports.llm import LLMUnavailable, StructuredRequest, StructuredResult

type Responder = Callable[[StructuredRequest], dict[str, Any]]


class FakeLLM:
    """Answers each request with what the responder returns; records every request."""

    def __init__(self, responder: Responder | None = None) -> None:
        self.responder = responder
        self.requests: list[StructuredRequest] = []

    async def complete_structured(self, request: StructuredRequest) -> StructuredResult:
        self.requests.append(request)
        if self.responder is None:
            raise LLMUnavailable("fake model is down")
        return StructuredResult(self.responder(request), "fake-model", 10, 10, 0.0, 1)


class MemoryStore:
    """ObjectStore kept in a dict."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    async def get(self, key: str) -> bytes:
        return self.objects[key][0]

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def presigned_url(self, key: str) -> str:
        return f"memory://{key}"
