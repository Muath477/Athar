# Sadu (سدو)

Sadu weaves many visitors' photos into one living picture of a heritage site's condition. A visitor photographs a mud-brick facade and gets a verified story of the place, read aloud in Arabic, plus a stamp in their Sadu Passport. Behind the scenes, agents compare the photo with the authority's baseline, look for new damage, and pin only evidence-backed findings on a 3D model of the site. Anything uncertain goes to an expert or back to the visitor as a retake request.

Round 1 MVP for the agentX Riyadh hackathon, Culture & Heritage track (team Athar). Planning documents are in [docs/](docs/README.md).

## Run it

You need Docker with Compose v2.

```bash
cp .env.example .env          # add keys if you have them; it runs without
docker compose up --build     # first build takes a few minutes
```

Then open:

| | URL |
|---|---|
| Visitor app | http://localhost:3000 |
| Dashboard | http://localhost:3000/dashboard |
| API docs | http://localhost:8000/api/docs |

The `seed` service loads the demo region pack (`region-packs/demo`), a synthetic test building with four facades. It is not a heritage site. Create a dashboard account with:

```bash
docker compose run --rm -e SADU_NEW_USER_PASSWORD='choose-12-chars-or-more' api \
  python -m sadu.cli create-user inspector@example.com --role expert
```

Roles are `inspector`, `expert` (can also review) and `admin`. Test photos to upload are in `region-packs/demo/test-photos/`.

For a public demo on a VM, set `SADU_DOMAIN` and `SADU_ENV=prod` in `.env`, then `docker compose --profile prod up -d`. Caddy gets TLS certificates and serves the app on 443.

## Environment

| Variable | Needed for | Without it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Damage judgment, plan, story drafting, claim checks | Changes go to the expert queue unjudged; stories fall back to verbatim official text or none |
| `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | Arabic audio (`ar-SA-HamedNeural`) | Story shows as text only |
| `SADU_DEMO_MODE` | `true` serves recorded model answers before calling the API | Live calls; recordings are still used if a call fails |
| `SADU_DAILY_LLM_BUDGET_USD` | Daily spend cap, default 10 | Calls past the cap fail over to the fallbacks |
| `SENTRY_DSN_API` | Error reports | Errors are only in the logs |
| `POSTGRES_PASSWORD`, `S3_*` | Change for anything public | Dev defaults |
| `SADU_DOMAIN` | Production profile | `localhost` |

## How a photo flows

1. The visitor app sends the photo with consent flags. Location and heading are dropped without consent. EXIF is stripped and faces are blurred before anything is stored.
2. The orchestrator plans steps from a fixed set. The Identifier finds the site and facade (GPS when allowed, then feature matching against the baselines) and asks the visitor when it is unsure.
3. The Monitor checks photo quality, aligns the photo to the baseline, and builds a difference map. Claude judges only the numbered regions that changed.
4. The Verifier applies a fixed rule: a finding is published as *likely* or *confirmed* only with evidence (baseline, aligned photo, difference map). Two independent contributors make it *confirmed*. Uncertain or urgent findings pause the run for an expert.
5. The Guide returns a story built from curated sources. Each sentence is checked against its cited source and labelled.

Every step has a timeout, retries and a fallback, and status updates stream to the phone over server-sent events.

## Project layout

```
backend/            FastAPI modular monolith (Python 3.13, uv)
  src/sadu/modules/ one folder per domain: sites, capture, inspection, verification,
                    stories, missions, passport, agents, admin
  src/sadu/shared/  config, database, storage, ports and adapters (Claude, Azure, S3)
  alembic/          migrations
  tests/            unit and integration tests
  eval/             vision evaluation on the demo pack
frontend/           Next.js 16 app: visitor PWA and dashboard, Arabic RTL
infra/              database image, storage start script, Caddyfile
region-packs/demo/  synthetic demo building, baselines, test photos, sources
docs/               plan, architecture, ADRs, threat model
```

Module boundaries are enforced by import-linter: domain code imports no framework, layers point inward, and modules only use each other's `api.py`.

## Tests and checks

Backend, from `backend/` (needs Postgres from compose):

```bash
uv sync
docker compose up -d db
docker compose exec db createdb -U sadu sadu_test
DATABASE_URL=postgresql+psycopg://sadu:dev@localhost:5432/sadu_test uv run alembic upgrade head
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports
uv run python -m eval.run
```

Tests use their own `sadu_test` database and refuse to run committing tests against any database whose name does not end in `_test`. The face blur model is downloaded into `backend/models/` by the Docker build and by CI; for local runs, copy the download step from `.github/workflows/ci.yml`.

Frontend, from `frontend/`:

```bash
npm ci
npm run lint && npm run typecheck && npm run build
```

CI runs all of the above plus `pip-audit`, `npm audit`, gitleaks, Semgrep, Trivy and a render of every Mermaid diagram in `docs/`.

## Demo day checklist

- [ ] Real baseline photos and region pack loaded; `uv run python -m eval.run` re-run on them
- [ ] Run each scripted photo once with the API key so its answers are recorded, then set `SADU_DEMO_MODE=true`
- [ ] Story audio generated once per facade (needs the Azure key)
- [ ] Expert account created and logged in on the laptop
- [ ] Spending limits set on the Anthropic and Azure accounts
- [ ] Phone on the venue network; camera and location permissions granted for the site
- [ ] Backup: screen recording of the full flow

## Privacy

Location is used only with consent and discarded once the facade is known. Photos are kept 30 days unless they are evidence for a published finding. A visitor can delete their passport and every photo that is not evidence from the passport page. See [the threat model](docs/06-security/threat-model.md).
