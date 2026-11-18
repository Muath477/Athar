import httpx
import structlog

from sadu.modules.assistant.application.ports import ReportNotice

log = structlog.get_logger()


class NoSpecialistChannel:
    @property
    def name(self) -> str:
        return "none"

    async def deliver(self, notice: ReportNotice) -> bool:
        return False


class WebhookSpecialistChannel:
    def __init__(
        self, url: str, *, timeout_s: float = 10.0, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._url = url
        self._timeout_s = timeout_s
        self._transport = transport

    @property
    def name(self) -> str:
        return "webhook"

    async def deliver(self, notice: ReportNotice) -> bool:
        text = f"ملف تدقيق من أثر بانتظار اعتماد المختص: {notice.conversation_title} · {notice.link}"
        if notice.note_ar:
            text += f" · {notice.note_ar}"
        payload = {
            "text": text,
            "file_name": notice.file_name,
            "link": notice.link,
            "conversation": notice.conversation_title,
            "note": notice.note_ar,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s, transport=self._transport) as client:
                response = await client.post(self._url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError:
            log.warning("specialist_webhook_failed", file_name=notice.file_name)
            return False
        return True
