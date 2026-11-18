# Athar API

FastAPI modular monolith for Athar (Python 3.13, uv). The package is still called `sadu`, the project's first name.

## Layout

```
src/sadu/
  main.py                 app factory, routers, background loops started in the lifespan
  cli.py                  seed region packs, create accounts
  shared/                 config, database, object store, LLM port and adapters, resilience, vocabulary
  modules/<module>/
    api.py                the only file other modules may import
    domain/               rules and value objects, no framework imports
    application/          use cases and ports
    infrastructure/       ORM rows, OpenCV, HTTP clients, PDF rendering
    interface/            FastAPI routes and schemas
alembic/versions/         migrations
tests/unit/               pure tests, no database
tests/integration/        API and repository tests against PostGIS
eval/                     vision evaluation, wall map scoring, satellite backtest
scripts/                  demo pack builder
```

import-linter (`[tool.importlinter]` in `pyproject.toml`) enforces three contracts: domain layers import no framework, layers inside a module point inward, and modules depend on each other only in this order:

```mermaid
flowchart TD
  assistant --> mapping & reports & watch & treatments & sites & capture
  agents --> capture & inspection & verification & stories & missions & passport & sites
  ingest --> mapping & capture & sites
  reports --> mapping & treatments & sites
  models --> mapping
  watch --> missions & sites
  missions --> verification & capture & sites
  mapping --> capture & sites & treatments
  verification --> sites
  passport --> sites
```

Every module except `capture`, `inspection`, `passport` and `stories` also imports `admin` for users, permissions and the audit log; it is left out of the graph to keep it readable.

## Modules

| Module | Owns |
|---|---|
| `admin` | Users, sessions, roles and permissions, site scope, audit log, model cost counter |
| `agents` | LangGraph run per visitor photo, finding reviews, passport deletion, retention purge |
| `assistant` | Staff chat, skills in `assistant/skills/*.md`, tools, audit files, pending sends |
| `capture` | EXIF strip, YuNet face blur, resize, idempotent uploads |
| `ingest` | Devices, ingest jobs and worker, camera capture with SSRF checks, GPS facade matching |
| `inspection` | Quality gate, alignment to baseline, difference map, model judgment |
| `mapping` | Wall maps: rectification, grid, glossary, detectors (`build_detector`), elements, corrections, ten-step workflow, approval, accuracy, notices |
| `missions` | Photo missions for coverage gaps and ground checks |
| `models` | Own-model registry and `GET /ml/training-export` |
| `passport` | Anonymous visitor passports |
| `reports` | Wall report PDF, elements CSV, site condition JSON/PDF/CSV, assistant audit PDF |
| `sites` | Region packs, sites, facades, baselines, field photography permit |
| `stories` | Story sources, retrieval, drafted claims, cached stories |
| `treatments` | Treatment catalog and plans |
| `verification` | Evidence rule, findings, review queue, pins |
| `watch` | Sentinel-2 screening, risk, early warning, alert webhook |

## Run

The API reads `.env` in the working directory; the defaults match the `db` and `storage` services in the root `docker-compose.yml`.

```bash
docker compose -f ../docker-compose.yml up -d db storage
uv sync
mkdir -p models && curl -fsSL -o models/face_detection_yunet_2023mar.onnx \
  https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
uv run alembic upgrade head
uv run python -m sadu.cli seed --pack demo
uv run python -m sadu.cli seed --pack riyadh
SADU_NEW_USER_PASSWORD='choose-12-chars-or-more' uv run python -m sadu.cli create-user you@example.com --role admin
uv run uvicorn sadu.main:app --reload --port 8000
```

- `seed --pack <name>` imports `../region-packs/<name>` (`SADU_REGION_PACKS_DIR`). With `SADU_DEMO_MODE=true`, seeding `demo` also registers the demo camera.
- `create-user <email> --role <role>` takes `inspector` (default), `site_manager`, `expert`, `authority`, `ml_engineer` or `admin`, and a password of at least 12 characters from `SADU_NEW_USER_PASSWORD` or a prompt.
- API docs: http://localhost:8000/api/docs (not served when `SADU_ENV=prod`). Health: `GET /api/v1/healthz`.

The lifespan starts six loops in the same process: mission dispatch, satellite scans, the ingest worker, camera capture, the retention purge and overdue-approval reminders. Run one API process; a second one would duplicate scheduled captures.

All settings are in `src/sadu/shared/config.py`; the root [README](../README.md#environment-variables) lists them with defaults.

## Migrations

```bash
uv run alembic revision -m "add something"
uv run alembic upgrade head
uv run alembic check
```

Files are named `YYYYMMDD_<revision>_<slug>.py`. Keep one head; CI runs `alembic check` to catch models that drift from the migrations.

## Tests and checks

```bash
docker compose -f ../docker-compose.yml exec db createdb -U sadu sadu_test
DATABASE_URL=postgresql+psycopg://sadu:dev@localhost:5432/sadu_test uv run alembic upgrade head
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run python -m eval.run
uv run pytest ../ml/tests
```

- Tests use `sadu_test` by default. Integration tests that commit are skipped on a database whose name does not end in `_test`.
- Tests replace the hosted model and object store with fakes (`tests/fakes.py`) and cameras and model servers with fake clients or mock transports, so no key or network is needed.
- The face blur model must be in `models/`; the Docker build and CI download it.
- WeasyPrint needs Pango and HarfBuzz from the system (`libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-noto-core` on Debian and Ubuntu).

Evaluation:

```bash
uv run python -m eval.score_maps ../path/to/walls --min-accuracy 0.8
uv run python -m eval.backtest_watch run --sites at-turaif --start 2024-03-01 --end 2026-11-01 --out watch-backtest
uv run python -m eval.backtest_watch score watch-backtest/alerts.csv
```

The wall folder format is in [docs/10-damage-maps.md](../docs/10-damage-maps.md#measuring-accuracy-before-the-demo).
