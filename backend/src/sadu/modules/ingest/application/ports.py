from dataclasses import dataclass
from typing import Any, Protocol


class CameraUnreachable(Exception):
    def __init__(self, reason: str, **details: Any) -> None:
        super().__init__(reason)
        self.reason = reason
        self.details = details


@dataclass(frozen=True)
class CameraTarget:
    snapshot_url: str | None
    rtsp_url: str | None
    username: str | None = None
    password: str | None = None


class CameraClient(Protocol):
    async def snapshot(self, target: CameraTarget) -> bytes: ...
