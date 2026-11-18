from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Notice:
    kind: str
    text: str
    link: str
    fields: Mapping[str, Any] = field(default_factory=dict)


class Notifier(Protocol):
    async def send(self, notice: Notice) -> None: ...
