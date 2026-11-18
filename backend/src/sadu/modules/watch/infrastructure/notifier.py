import httpx
import structlog

from sadu.modules.watch.application.ports import AlertMessage

log = structlog.get_logger()


class NoNotifier:
    async def notify(self, message: AlertMessage) -> None:
        return None


class WebhookNotifier:
    def __init__(
        self, url: str, *, timeout_s: float = 10.0, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._url = url
        self._timeout_s = timeout_s
        self._transport = transport

    async def notify(self, message: AlertMessage) -> None:
        text = (
            f"تنبيه أثر: {message.site_name_ar} · {message.level} ({message.score}) · "
            f"{'، '.join(message.threats_ar)} · {message.link}"
        )
        payload = {
            "text": text,
            "site": message.site_name_ar,
            "level": message.level,
            "score": message.score,
            "threats": list(message.threats_ar),
            "trend": message.trend,
            "link": message.link,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s, transport=self._transport) as client:
                response = await client.post(self._url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError:
            log.warning("alert_webhook_failed", site=message.site_name_ar)
