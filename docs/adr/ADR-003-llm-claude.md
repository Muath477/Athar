# ADR-003: Claude Sonnet 5.5 and Haiku 5.5 behind an LLM port

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

Damage judgment needs strong vision over three images and Arabic output; routing, ranking and claim checks need to be cheap and fast. The model must be swappable.

## Decision

`claude-sonnet-5-5` for damage judgment and story drafting; `claude-haiku-5-5` for planning, mission ranking, facade tie-break and claim entailment. Called through an `LLMPort` (`complete_structured(model_role, system, content, schema, timeout) -> dict`) with one Anthropic adapter using the `anthropic` Python SDK and structured outputs via `output_config={"format": {"type": "json_schema", "schema": ...}}` (or `messages.parse(output_format=PydanticModel)`). Thinking is adaptive (default); effort set per role. No `temperature` (rejected by current models). Check `stop_reason` before reading content; handle `refusal` by routing to expert review. SDK `max_retries=2`, per-call timeout from §8.

## Alternatives considered

- **Open-weights VLM self-hosted**: no per-call cost, but GPU hosting and weaker Arabic output in 3 days.
- **One model for everything**: simpler, but Sonnet for routing wastes money and latency; Haiku for judgment risks accuracy.
- **Other hosted VLMs**: possible behind the same port; not evaluated in Round 1.

## Consequences

- Prices (Anthropic first-party, cached skill table dated 2026-11-03): Sonnet 5.5 USD 2 / 10 per MTok in/out; Haiku 5.5 USD 0.10 / 0.50. Estimated <= USD 0.03 per photo (see 04-stack).
- Photos (blurred, EXIF-free) leave the Kingdom for inference: flagged for PDPL review before any pilot; `inference_geo` options to be checked then (TBD).
- Prompt files and JSON schemas are versioned; eval harness reruns on every prompt change.

## Versions

anthropic 2.9.0 (PyPI, 2026-11-16). Structured output request shape (`output_config.format`) checked in the SDK migration notes via Context7.
