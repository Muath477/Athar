import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.shared.config import Settings
from sadu.shared.errors import TooManyRequests
from sadu.shared.storage import ObjectStore

type UnitOfWork = Callable[[], AbstractAsyncContextManager[AsyncSession]]

API_PREFIX = "/api/v1"


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_s: int) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - window_s:
            hits.popleft()
        if len(hits) >= limit:
            raise TooManyRequests("rate_limited", retry_after_s=int(hits[0] + window_s - now) + 1)
        hits.append(now)


@dataclass
class AppState:
    settings: Settings
    unit_of_work: UnitOfWork
    store: ObjectStore
    runner: Any
    rate_limiter: RateLimiter = field(default_factory=RateLimiter)


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
