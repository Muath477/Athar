from typing import Protocol


class SpeechUnavailable(Exception):
    pass


class TextToSpeechPort(Protocol):
    async def synthesize(self, text: str, voice: str) -> bytes:
        """Return MP3 audio for `text`."""
        ...
