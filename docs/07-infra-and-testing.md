# 07 · Infrastructure, monitoring and quality

Written 2026-11-16. Image tags and package versions come from [04-stack.md](04-stack.md).

## 1. Docker

### Images

| Image | Base | Stages | Runtime user | Health check |
|---|---|---|---|---|
| `sadu-api` | `python:3.13-slim` | 1) `builder`: install build deps, `uv`/pip install into a venv from the lockfile, download YuNet ONNX and BGE-M3 weights; 2) `runtime`: copy venv + model files + `src/`, install only runtime libs (libgl not needed with headless OpenCV; Pango only if WeasyPrint is enabled) | `sadu` (uid 10001), read-only root FS, `/tmp` as tmpfs | `GET /healthz` every 15 s |
| `sadu-web` | `node:24-alpine` | 1) `deps`: `npm ci`; 2) `build`: `next build` with `output: "standalone"`; 3) `runtime`: copy `.next/standalone`, `.next/static`, `public` | `node` | `wget -qO- http://localhost:3000/api/health` |
| `sadu-db` | `postgis/postgis:18-3.7` + pgvector for PG 18 | pgvector extension files copied from `pgvector/pgvector:0.8.7-pg18-trixie` | `postgres` | `pg_isready` |
| storage | SeaweedFS (pinned tag) | n/a | non-root where supported | S3 endpoint check |
| `caddy` (demo VM only) | `caddy:2.11.9-alpine` | n/a | default | n/a |

### docker-compose (local dev)

Services: `db`, `storage`, `api` (bind-mount `src/` and `--reload` in the dev profile), `web` (`next dev`), plus a one-shot `migrate` (Alembic upgrade) and `seed` (import the demo region pack). The demo VM uses the same file with a `prod` profile that adds `caddy` and drops bind mounts.

### `.env.example` (names only)

```dotenv
# shared
SADU_ENV=dev                      # dev | prod
SADU_PUBLIC_ORIGIN=http://localhost:3000
# database
POSTGRES_USER=sadu
POSTGRES_PASSWORD=
POSTGRES_DB=sadu
DATABASE_URL=postgresql+psycopg://sadu:${POSTGRES_PASSWORD}@db:5432/sadu
# object storage
S3_ENDPOINT_URL=http://storage:8333
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET=sadu
# LLM
ANTHROPIC_API_KEY=
SADU_MODEL_MAIN=claude-sonnet-5-5
SADU_MODEL_FAST=claude-haiku-5-5
SADU_DAILY_LLM_BUDGET_USD=10
# TTS
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
SADU_TTS_VOICE=ar-SA-HamedNeural
# observability
SENTRY_DSN_API=
NEXT_PUBLIC_SENTRY_DSN=
# features
SADU_DEMO_MODE=false              # serve cached results for scripted photos
SADU_ENABLE_YOLO=false
```

## 2. Observability

| Signal | Tool | What is captured |
|---|---|---|
| LLM calls | `llm_calls` table | One row per model call: agent, model, observation id, latency, token counts, cost. Rule reasons are stored on each finding. Images are never logged. |
| Errors | Sentry (API + web) | Exceptions with release version, request ID, route; `send_default_pii=False`; before-send hook strips query strings and headers. Source maps uploaded for the web build. |
| Logs | structlog JSON to stdout, collected by Docker | `request_id`, `observation_id`, module, event, duration. No tokens, emails, coordinates or image data. |
| Cost per photo | `llm_calls` table + `GET /admin/costs` | Sum of cost per observation, mean and p95 per day, by agent and model. Alert (log + Sentry message) when the daily total passes `SADU_DAILY_LLM_BUDGET_USD`; uploads then switch to story-only mode. |
| Latency | API middleware histogram in logs; per-call latency in `llm_calls` | Upload-to-pin time per observation for the D2 driver. |

## 3. Testing

### Layers

| Layer | Tool | Scope | Examples |
|---|---|---|---|
| Unit (domain) | pytest | Pure rules, no I/O | Confidence label rule (every branch in §9 of the architecture), severity floor, facade UV → xyz, heading score, plan invariants, mission priority, retention dates |
| Unit (CV) | pytest + fixture images | Pipeline functions on small fixtures | Quality gate thresholds, alignment accepts a known pair and rejects an unrelated photo, lighting flag on a synthetic shadow |
| Integration (module boundary) | pytest + real Postgres/PostGIS/pgvector and SeaweedFS in compose (or Testcontainers) | Each module's `api.py` facade with its infrastructure | `find_sites_near`, upload idempotency, EXIF/face fixtures, publish rejects findings without evidence (DB CHECK), retrieval returns chunks for the site, interrupt + resume round trip |
| Contract | pytest | JSON schemas in docs match Pydantic models; OpenAPI snapshot | Schema drift fails CI |
| Architecture | import-linter | Module and layer rules from ADR-001 | No cycles; domain imports no framework |
| Unit (frontend) | Vitest 5 in Node mode (`npm test`) | Pure logic in `src/**/*.test.ts` | Route geometry and progress (next turn, off route, arrival), Google Maps links, Arabic distance and time |
| End to end | Playwright 1.65 (`npm run e2e`, `frontend/e2e/`) | The stack in compose with `SADU_DAMAGE_DETECTOR=none` | Phone: At-Turaif page with walking and driving directions; home page. Desktop: expert logs in, maps a wall from a photo, approves it, downloads the PDF report. Planned: photo to pin with recorded model answers |
| Evaluation | `eval/run.py` | The 50-image set against the real pipeline (real LLM) | Prints every success metric (below) |

### Evaluation harness

Command: `docker compose run --rm api python -m eval.run --set data/testset --out eval/results/<name>.md`

Inputs: `data/testset/labels.csv` (per photo: facade code, has_change, damage_type, change box in baseline pixels), `data/testset/false_reports/` (10 photos meant to fool the system: shadows, wet patches after watering, a wrong building, a photo of a screen, a photo with written instructions), and `data/stories/questions.csv` (20 questions with reference answers and allowed sources).

Output table (printed and written to Markdown):

| Metric | Definition | Target |
|---|---|---|
| Detection precision | True positive changes / predicted changes (published or sent to review), matched by IoU >= 0.1 in facade UV | >= 80% |
| Detection recall | True positive changes / labeled changes | >= 80% |
| Facade accuracy | Photos whose identified facade equals the label | >= 90% |
| False reports stopped | False-report photos that end as discard, retake or expert reject | >= 9 of 10 |
| Evidence coverage | Published findings with baseline, photo and diff keys present | 100% |
| Story hallucination | Unsupported claims / total claims, with Verifier on vs off (human-labeled on the 20 questions) | Clear reduction (report both numbers) |
| Cost per photo | Mean and p95 USD | <= 0.05 mean |
| Latency | Upload to final state p50 / p95 | p95 <= 30 s |

The harness also writes a confusion table by damage type and lists every false positive with its images so the team can show them openly in the demo.

### CI pipeline (GitHub Actions, every push and PR)

1. `backend`: ruff format check, ruff lint, mypy (strict on `domain/` and `application/`), import-linter, pytest unit + integration (services: Postgres image, SeaweedFS).
2. `frontend`: eslint, `tsc --noEmit`, Vitest, `next build`, `npm audit`.
3. `security`: gitleaks, pip-audit, npm audit, Semgrep (see threat model §6).
4. `images`: build `api`, `web`, `db`; Trivy scan; fail on HIGH/CRITICAL.
5. `e2e`: after `backend` and `frontend` pass, compose up `api` and `web`, seed both region packs, create a throwaway expert, run Playwright in Chromium; the HTML report and service logs are kept on failure.
6. `docs`: render every Mermaid block with mermaid-cli; fail on a syntax error.

The evaluation harness runs manually (it spends API credit) and its results file is committed.

### Test rules

- Domain rules get a test per branch before the code that uses them.
- Each bug found in rehearsal gets a failing test first.
- While fixing, re-run only failing tests; run the full suite once before merging.
