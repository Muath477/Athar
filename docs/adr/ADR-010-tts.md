# ADR-010: Azure AI Speech with a Saudi Arabic neural voice, cached

- Status: Accepted, amended by [ADR-016](ADR-016-build-time-changes.md): REST instead of the SDK
- Date: 2026-11-16

## Context

Stories must play as Arabic audio with a Saudi voice.

## Decision

`TTSPort.synthesize(text_ar, voice) -> bytes` with an Azure AI Speech adapter. Voices: `ar-SA-HamedNeural` (male) or `ar-SA-ZariyahNeural` (female), confirmed in Microsoft Learn language support on 2026-11-16. Audio is generated once per story version, stored in object storage and served by presigned URL. Demo stories are pre-generated.

## Alternatives considered

- **Google Cloud TTS / ElevenLabs / open-source Arabic TTS**: possible behind the same port; not checked for ar-SA voices in Round 1.
- **Browser speechSynthesis**: free but voice availability varies per phone.

## Consequences

- One Azure key in env; region choice affects latency and data location (TBD).
- If TTS fails, text still shows.

## Versions

azure-cognitiveservices-speech 1.53.1 (PyPI, 2026-11-16).
