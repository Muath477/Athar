"""Demo resilience (D3): replay recorded LLM answers when the network or API fails."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import structlog

from sadu.shared.ports.llm import LLMPort, LLMUnavailable, StructuredRequest, StructuredResult

log = structlog.get_logger()


class CachedLLM:
    """Records every successful answer; serves the recording when the live call fails.

    The key covers the prompt, schema and image bytes, so a different photo never gets
    another photo's answer.
    """

    def __init__(self, live: LLMPort, cache_dir: Path, *, prefer_cache: bool) -> None:
        self._live = live
        self._cache_dir = cache_dir
        self._prefer_cache = prefer_cache
        cache_dir.mkdir(parents=True, exist_ok=True)

    async def complete_structured(self, request: StructuredRequest) -> StructuredResult:
        path = self._cache_dir / f"{request.agent}-{request_fingerprint(request)}.json"
        if self._prefer_cache and path.is_file():
            return self._replay(path)
        try:
            result = await self._live.complete_structured(request)
        except LLMUnavailable:
            if path.is_file():
                log.warning("llm_served_from_cache", agent=request.agent)
                return self._replay(path)
            raise
        path.write_text(json.dumps(asdict(result), ensure_ascii=False), encoding="utf-8")
        return result

    @staticmethod
    def _replay(path: Path) -> StructuredResult:
        recorded = json.loads(path.read_text(encoding="utf-8"))
        return StructuredResult(**{**recorded, "cost_usd": 0.0, "latency_ms": 0})


def request_fingerprint(request: StructuredRequest) -> str:
    digest = hashlib.sha256()
    for part in (request.agent, request.system, request.text, json.dumps(request.schema, sort_keys=True)):
        digest.update(part.encode("utf-8"))
    for image in request.images:
        digest.update(hashlib.sha256(image.data).digest())
    return digest.hexdigest()[:32]
