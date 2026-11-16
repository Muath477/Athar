import asyncio
from collections.abc import Awaitable, Callable

import structlog

log = structlog.get_logger()


async def call_with_policy[T](
    operation: str,
    call: Callable[[], Awaitable[T]],
    *,
    timeout_s: float,
    retries: int = 0,
    backoff_s: float = 0.5,
) -> T:
    """Run `call` with a per-attempt timeout and exponential backoff between attempts.

    Re-raises the last error so the caller decides on the fallback; a fallback hidden
    here would make demo failures look like successes.
    """
    attempt = 0
    while True:
        try:
            return await asyncio.wait_for(call(), timeout=timeout_s)
        except Exception as error:
            if attempt >= retries:
                log.warning("external_call_failed", operation=operation, error=type(error).__name__)
                raise
            attempt += 1
            await asyncio.sleep(backoff_s * 2 ** (attempt - 1))
