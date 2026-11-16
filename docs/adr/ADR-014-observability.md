# ADR-014: Langfuse for LLM traces, Sentry for errors, structlog for logs

- Status: Partly superseded by [ADR-016](ADR-016-build-time-changes.md): Langfuse is not used in Round 1
- Date: 2026-11-16

## Context

We must show each agent step, its cost and latency, and catch errors fast during the demo.

## Decision

Langfuse (cloud project) traces each graph run with one span per node and per LLM call; traces include prompts, structured outputs, token counts and cost, but **never image bytes** (only object keys). Sentry SDKs in API and web with PII scrubbing and `send_default_pii` off. structlog JSON logs with request IDs. A `llm_calls` table is the source of truth for the cost-per-photo counter.

## Alternatives considered

- **Self-hosted Langfuse**: keeps data local but needs ClickHouse, Redis and more RAM on the VM.
- **OpenTelemetry only**: standard, but no LLM-specific UI without extra tooling.

## Consequences

- Traces leave the VM: prompts contain no personal data by construction (blurred photos are not attached).
- Langfuse cloud region choice TBD.

## Versions

langfuse 5.2.0, sentry-sdk 2.75.0, structlog 26.1.0 (PyPI); @sentry/nextjs 11.13.0 (npm) (2026-11-16).
