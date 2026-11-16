# ADR-004: One PostgreSQL 18 database with PostGIS and pgvector

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

We need relational data (sites, findings, reviews), spatial queries (GPS to site, distance), vector search (story retrieval) and the LangGraph checkpointer. Running separate stores costs ops time.

## Decision

PostgreSQL 18 with PostGIS 3.7 and pgvector 0.8.x in one database. Local image built `FROM postgis/postgis:18-3.7` with the compiled pgvector extension copied from `pgvector/pgvector:0.8.7-pg18-trixie`, which uses the same Debian release and PostgreSQL major ([ADR-016](ADR-016-build-time-changes.md)). SQLAlchemy 2.1 + GeoAlchemy2 + Alembic; psycopg 3 driver.

## Alternatives considered

- **Separate vector DB** (Qdrant, etc.): better at scale, unnecessary for a few hundred chunks.
- **SQLite + SpatiaLite**: lighter, but no good pgvector equivalent and the LangGraph checkpointer we want is Postgres.
- **Managed Postgres**: easier backups, but needs PostGIS + pgvector support on the provider; keep as a pilot option.

## Consequences

- One backup covers everything.
- The DB image is custom (PostGIS + pgvector) and must be scanned like our other images.
- The brief targeted PostGIS 3.6; the current image tag is 3.7, which we use.

## Versions

Docker Hub tags seen 2026-11-16: `postgres:18.7`, `postgis/postgis:18-3.7`, `pgvector/pgvector:0.8.7-pg18-trixie`. PyPI: sqlalchemy 2.1.8, geoalchemy2 0.21.0, alembic 1.20.1, psycopg 3.3.9, pgvector (python) 0.5.1.
