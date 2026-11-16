from xml.sax.saxutils import escape, quoteattr

import httpx

from sadu.shared.ports.speech import SpeechUnavailable
from sadu.shared.resilience import call_with_policy

OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
TIMEOUT_S = 10.0


class AzureSpeech:
    def __init__(self, key: str, region: str, client: httpx.AsyncClient | None = None) -> None:
        self._key = key
        self._url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
        self._client = client or httpx.AsyncClient()

    async def synthesize(self, text: str, voice: str) -> bytes:
        ssml = (
            f"<speak version='1.0' xml:lang='ar-SA'><voice name={quoteattr(voice)}>"
            f"{escape(text)}</voice></speak>"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self._key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": OUTPUT_FORMAT,
            "User-Agent": "sadu",
        }

        async def post() -> bytes:
            response = await self._client.post(self._url, content=ssml.encode(), headers=headers)
            response.raise_for_status()
            return response.content

        try:
            return await call_with_policy("azure_tts", post, timeout_s=TIMEOUT_S, retries=1)
        except (httpx.HTTPError, TimeoutError) as error:
            raise SpeechUnavailable(str(error)) from error


class NoSpeech:
    async def synthesize(self, text: str, voice: str) -> bytes:
        raise SpeechUnavailable("text to speech is not configured")
