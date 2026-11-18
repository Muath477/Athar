import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from sadu.modules.mapping.application.element_prompt import completion_body, wall_messages

DEFAULT_URL = "http://localhost:8080/v1"
DEFAULT_MODEL = "athar-damage"
DEFAULT_TIMEOUT_S = 120.0


@dataclass(frozen=True)
class ChatEndpoint:
    url: str = DEFAULT_URL
    model: str = DEFAULT_MODEL
    timeout_s: float = DEFAULT_TIMEOUT_S
    token: str | None = None
    json_schema: bool = True

    def complete(self, messages: list[dict[str, Any]]) -> str:
        body = completion_body(self.model, messages, json_schema=self.json_schema)
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            f"{self.url.rstrip('/')}/chat/completions", data=json.dumps(body).encode(), headers=headers
        )
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            payload = json.loads(response.read())
        return str(payload["choices"][0]["message"]["content"])

    def map_wall(self, jpeg: bytes) -> str:
        return self.complete(wall_messages(jpeg))
