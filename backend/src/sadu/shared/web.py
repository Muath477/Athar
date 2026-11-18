import time
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.shared.adapters.webhook import NoNotifier
from sadu.shared.config import Settings
from sadu.shared.errors import TooManyRequests
from sadu.shared.ports.notify import Notifier
from sadu.shared.storage import ObjectStore

type UnitOfWork = Callable[[], AbstractAsyncContextManager[AsyncSession]]

API_PREFIX = "/api/v1"


FORGET_IDLE_EVERY_CHECKS = 1000


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._windows: dict[str, int] = {}
        self._clock = clock
        self._checks = 0

    def check(self, key: str, limit: int, window_s: int) -> None:
        now = self._clock()
        self._checks += 1
        if self._checks % FORGET_IDLE_EVERY_CHECKS == 0:
            self._forget_idle(now)
        hits = self._hits.setdefault(key, deque())
        self._windows[key] = window_s
        while hits and hits[0] <= now - window_s:
            hits.popleft()
        if len(hits) >= limit:
            raise TooManyRequests("rate_limited", retry_after_s=int(hits[0] + window_s - now) + 1)
        hits.append(now)

    @property
    def tracked_keys(self) -> int:
        return len(self._hits)

    def _forget_idle(self, now: float) -> None:
        idle = [key for key, hits in self._hits.items() if not hits or hits[-1] <= now - self._windows[key]]
        for key in idle:
            del self._hits[key]
            del self._windows[key]


@dataclass
class AppState:
    settings: Settings
    unit_of_work: UnitOfWork
    store: ObjectStore
    runner: Any
    rate_limiter: RateLimiter = field(default_factory=RateLimiter)
    notifier: Notifier = field(default_factory=NoNotifier)


def app_state(request: Request) -> AppState:
    state: AppState = request.app.state.sadu
    return state


async def db_session(state: Annotated[AppState, Depends(app_state)]) -> AsyncIterator[AsyncSession]:
    async with state.unit_of_work() as session:
        yield session


State = Annotated[AppState, Depends(app_state)]
Session = Annotated[AsyncSession, Depends(db_session)]


def public() -> None: ...


def limit_per_ip(name: str, limit: int, window_s: int) -> Callable[[Request, AppState], None]:
    def dependency(request: Request, state: State) -> None:
        state.rate_limiter.check(f"{name}:{client_ip(request)}", limit, window_s)

    return dependency


limit_public_reads = limit_per_ip("read", 240, 60)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
}


async def security_headers_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    response.headers.setdefault("Cache-Control", "no-store")
    return response
