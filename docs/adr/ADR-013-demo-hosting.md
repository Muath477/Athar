# ADR-013: One VM running docker compose behind Caddy

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

The demo must work from a public HTTPS URL (camera and geolocation require HTTPS) on Nov 21 and Nov 28-30.

## Decision

One cloud VM (4 vCPU, 8-16 GB RAM, Ubuntu LTS) runs the compose stack; Caddy terminates TLS with automatic certificates and sets security headers. Region: closest available to Riyadh (TBD by budget). Nightly `pg_dump` and bucket sync to a second location.

## Alternatives considered

- **PaaS per service**: less ops, but PostGIS + pgvector + OpenCV images complicate it.
- **Kubernetes**: unnecessary.

## Consequences

- Single point of failure; mitigated by the recorded demo and cached mode.
- Same compose file for local and demo keeps surprises low.

## Versions

caddy 2.11.9 (Docker Hub, 2026-11-16).
