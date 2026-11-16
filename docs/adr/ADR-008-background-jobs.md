# ADR-008: In-process background tasks and SSE, no queue in Round 1

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

Each photo triggers a 10-30 s agent run. A queue (Redis + worker) adds containers and failure modes.

## Decision

Start runs with FastAPI `BackgroundTasks` in the API process. Status changes are written to the DB and pushed to the visitor with Server-Sent Events (`sse-starlette`); clients can poll instead. Because the LangGraph checkpointer persists each step, a startup sweep resumes observations left in `processing` for > 2 minutes. Concurrency capped by an `asyncio.Semaphore` (4 runs) so the demo VM is not overloaded.

## Alternatives considered

- **Celery/RQ/Arq + Redis**: robust retries and scaling; not needed at demo volume.
- **Postgres-backed queue** (SKIP LOCKED): good next step without new infra; write a new ADR when needed.

## Consequences

- A crash loses at most the current step, which the sweep re-runs.
- CPU-heavy OpenCV work runs in a thread pool (`run_in_threadpool`) so the event loop stays free.
- Move to a queue when we need more than one API process or GPU workers.

## Versions

sse-starlette 3.7.0, fastapi 0.163.1 (PyPI, 2026-11-16).
