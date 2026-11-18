from typing import Any

import httpx
import structlog

from sadu.shared.ports.notify import Notice

log = structlog.get_logger()

WEBHOOK_TIMEOUT_S = 10.0


async def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    timeout_s: float = WEBHOOK_TIMEOUT_S,
    transport: httpx.AsyncBaseTransport | None = None,
) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout_s, transport=transport) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError:
        return False
    return True


class NoNotifier:
    async def send(self, notice: Notice) -> None:
        return None


class WebhookNotifier:
    def __init__(self, url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._url = url
        self._transport = transport

    async def send(self, notice: Notice) -> None:
        payload = {"kind": notice.kind, "text": f"{notice.text} · {notice.link}", "link": notice.link}
        if not await post_json(self._url, {**notice.fields, **payload}, transport=self._transport):
            log.warning("notice_webhook_failed", kind=notice.kind)
