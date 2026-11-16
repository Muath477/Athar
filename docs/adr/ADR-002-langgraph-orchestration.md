# ADR-002: LangGraph orchestrator-worker graph with Postgres checkpointer and interrupts

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

Judges look for real agentic behaviour: planning, tool use and decisions. We also need pauses for humans (visitor answers which facade; expert confirms an urgent finding) that survive restarts, and we need per-step traces.

## Decision

Use LangGraph `StateGraph`: an `orchestrator` node plans from a closed enum of steps and routes with `Command(goto=...)`; `identify`, `monitor`, `verify`, `guide` are worker nodes that call deterministic tools and single structured-output LLM calls. Human pauses use `interrupt(value)` and are resumed with `Command(resume=value)`. State is persisted with the Postgres checkpointer (`langgraph-checkpoint-postgres`, tables created by `setup()`), `thread_id = observation_id`. Mission dispatch is a separate small graph run on a schedule.

## Alternatives considered

- **Hand-written state machine**: fewer dependencies, but we would rebuild persistence, interrupts and tracing hooks.
- **Free-form tool-calling agent loop** (model picks any tool): looks more "agentic" but is harder to make safe against prompt injection and harder to test.
- **Claude Managed Agents**: hosted loop and sandbox, but our tools need local OpenCV, local DB and image files; adds a network hop per step.

## Consequences

- Interrupts re-execute the node from its start on resume, so nodes must put side effects after `interrupt()` and keep earlier writes idempotent.
- Checkpointing adds DB writes per step (acceptable at demo volume).
- The LLM chooses among allowed steps but cannot invent tool calls, which limits creativity and removes a class of injection attacks.

## Versions

langgraph 1.2.22, langchain-core 1.8.1, langgraph-checkpoint-postgres 3.2.1 (PyPI, 2026-11-16). `interrupt`/`Command(resume=)` semantics checked in LangGraph docs via Context7.
