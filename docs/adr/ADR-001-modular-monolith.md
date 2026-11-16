# ADR-001: Modular monolith with hexagonal module boundaries

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

Four people, three days, one live demo. The system has ten business areas (sites, capture, inspection, verification, stories, missions, passport, agents, reports, admin) that must stay separable so the product can grow after the hackathon. Operating several services would cost time we do not have (networking, auth between services, distributed tracing, deploys).

## Decision

One FastAPI deployable and one PostgreSQL database. Each business area is a module under `src/sadu/modules/<name>/` with `interface → application → domain → infrastructure` layers; dependencies point inward. Other modules may import only `modules/<name>/api.py`. Module tables are private. The module graph is acyclic and enforced in CI with import-linter contracts (layers + independence + forbidden imports). The LangGraph runtime is the `agents` module.

## Alternatives considered

- **Microservices** per agent: clean isolation, but too much ops work for 3 days and no scaling need.
- **Plain layered app without modules**: fastest to start, but agents, CV and verification would tangle and the Verifier rule would leak into routes.
- **Serverless functions**: cold starts hurt the 30 s budget; OpenCV and model weights make packages large.

## Consequences

- One container to build, deploy and debug; in-process calls are fast and simple.
- Boundaries are by convention plus import-linter, so discipline is needed in code review.
- A module can be extracted later (Inspection is the likely first, for GPU workers) because it already talks through a facade and events.

## Versions

import-linter 2.16 (PyPI, checked 2026-11-16).
