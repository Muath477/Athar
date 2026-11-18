<div align="center">

# أثر · Athar

**One photo of a mud wall becomes a damage map and a treatment plan that a conservator reviews.**
Visitors' photos keep the map current between expert surveys.

صورة واحدة لجدار طيني تتحول إلى خريطة تلف وخطة معالجة يراجعها المختص، وصور الزوار تبقي الخريطة محدّثة بين جولات الفحص.

[![CI](https://github.com/Muath477/Athar/actions/workflows/ci.yml/badge.svg)](https://github.com/Muath477/Athar/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.13-1f1a16?logo=python&logoColor=efe4d2)
![FastAPI](https://img.shields.io/badge/FastAPI-0.163-1f1a16?logo=fastapi&logoColor=efe4d2)
![Next.js](https://img.shields.io/badge/Next.js-16-1f1a16?logo=nextdotjs&logoColor=efe4d2)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18%20%2B%20PostGIS-1f1a16?logo=postgresql&logoColor=efe4d2)
![Docker](https://img.shields.io/badge/Docker-Compose-1f1a16?logo=docker&logoColor=efe4d2)

</div>

<p align="center"><img src="docs/assets/athar-pipeline.svg" alt="Animated pipeline: a wall photo has faces blurred, is straightened and split into a grid, damaged cells are marked and corrected by an expert, and a treatment plan with materials appears" width="100%"></p>

Built for the agentX Riyadh hackathon, Culture & Heritage track, Diriyah Gate Development Authority challenge: *detecting and mapping damage to mud walls*. Team Athar.

## Contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [UML](#uml)
- [Run it](#run-it)
- [Environment](#environment)
- [Tests and checks](#tests-and-checks)
- [Project layout](#project-layout)
- [Documentation](#documentation)
- [Privacy](#privacy)

## What it does

| For | Athar gives them |
|---|---|
| Conservation experts | A damage map of each wall from one photo: seven damage types (crack, plaster loss, moisture, basal erosion, surface erosion, partial collapse, graffiti), colour by type, strength by severity. They paint corrections with a brush and approve. |
| Site managers | A treatment plan per map: steps, materials scaled to the damaged area, tools, whether a specialist must supervise, and sources. Each new map lists what changed since the last approved one. |
| The authority | Model accuracy measured against expert decisions, cell by cell, so nobody has to take the model's word for it. |
| Visitors | A verified story of the place read aloud in Arabic and a passport stamp. A 3D view of the site on Google Maps, and the route there: steps in Arabic, a fly-through preview, and live tracking to the door. Their photos keep the condition record current. |

## How it works

### From a wall photo to a plan

1. An inspector picks a registered facade (or names a wall and gives its width and height), takes a photo and drags four handles to the wall corners.
2. The photo goes through the privacy step (EXIF stripped, faces blurred), then the wall is warped to a front-on view at its real aspect and split into a grid: 8 rows, columns follow the wall's shape.
3. The configured detector marks damaged cells. Claude gets the photo with the grid labels drawn on it; a ready model gets the plain photo (object detection) or one crop per cell (classification).
4. An expert paints corrections and approves. The model's original answer is kept, so `GET /maps/accuracy` shows how often the model agrees with the expert.
5. The treatment plan comes from `region-packs/treatments/earthen-najdi.json`, a draft catalog that a conservator must review before it is used as advice.

### Swap the model with one setting

<p align="center"><img src="docs/assets/detector-port.svg" alt="Animated diagram: the mapping module calls one DamageDetector port, which routes to Claude, a ready model over HTTP, a per-cell classifier, or manual labelling" width="90%"></p>

| `SADU_DAMAGE_DETECTOR` | Sends | Expects back |
|---|---|---|
| `claude` (default) | rectified wall with the labelled grid, one structured call | cell labels with type, severity, confidence |
| `http_detection` | rectified JPEG to `SADU_DETECTOR_URL` | Hugging Face object detection `[{label, score, box: {xmin, ymin, xmax, ymax}}]`, or `{"detections": [{label, score, box: [x0, y0, x1, y1]}]}` |
| `http_cell_classification` | one crop per grid cell | Hugging Face image classification `[{label, score}]` |
| `none` | nothing | the expert draws the map |

Model labels map to damage types with `SADU_DETECTOR_LABELS`, for example `{"spalling": "plaster_loss"}`. If the detector fails, the map is still saved empty so the expert can label it by hand. Details in [ADR-018](docs/adr/ADR-018-damage-detector-port.md).

### Changes over time

<p align="center"><img src="docs/assets/change-over-time.svg" alt="Animated comparison of two wall maps with new and resolved cells outlined" width="75%"></p>

### Visitors between surveys

<p align="center"><img src="docs/assets/visitor-flow.svg" alt="Animated flow: a visitor photo passes privacy, comparison with the baseline and the evidence rule, then becomes a pin or goes to an expert" width="90%"></p>

1. The visitor app sends the photo with consent flags. Location and heading are dropped without consent; EXIF is stripped and faces are blurred before anything is stored.
2. The orchestrator plans steps from a fixed set. The Identifier finds the site and facade (GPS when allowed, then feature matching against the baselines) and asks the visitor when it is unsure.
3. The Monitor checks photo quality, aligns the photo to the baseline and builds a difference map. Claude judges only the numbered regions that changed.
4. The Verifier publishes a finding as *likely* or *confirmed* only with evidence (baseline, aligned photo, difference map). Two independent contributors make it *confirmed*. Uncertain or urgent findings wait for an expert.
5. The Guide returns a story built from curated sources; each sentence is checked against its source and labelled.

Every external call has a timeout, retries and a fallback; status updates stream to the phone over server-sent events.

## Tech stack

| Layer | Technology | Version | Why |
|---|---|---|---|
| API | FastAPI, Pydantic, Uvicorn | 0.163.1 · 2.14.3 · 0.54.0 | Typed schemas and a generated OpenAPI contract |
| Agents | LangGraph with a Postgres checkpointer | 1.2.22 | Resumable runs that pause for a visitor answer or an expert |
| Model | Claude through the Anthropic SDK (`claude-sonnet-5-5`, `claude-haiku-5-5`) | SDK 2.9.0 | Vision plus structured output; one adapter behind a port |
| Ready models | Any HTTP endpoint (Hugging Face inference, own server) via httpx | 0.28.1 | Plug in a crack or damage model without code changes |
| Vision | OpenCV, scikit-image, Pillow, NumPy | 5.0 · 0.26 · 13.0 · 2.5 | Perspective rectification, grid drawing, alignment, SSIM, YuNet face blur |
| Data | PostgreSQL, PostGIS, pgvector, SQLAlchemy, Alembic | 18 · 3.7 · 0.8.7 · 2.1.8 · 1.20.1 | One store for records, geometry and story embeddings |
| Files | S3 API (SeaweedFS locally), boto3 | 4.54 · 1.44 | Private bucket, presigned URLs for five minutes |
| Speech | Azure AI Speech REST, `ar-SA-HamedNeural` | | Saudi Arabic voice for the visitor story |
| Web | Next.js App Router, React, TypeScript strict, Tailwind CSS | 16.4.6 · 19.3 · 5 · 4.3 | Arabic RTL PWA and dashboard; each page keeps its own components |
| 3D | three.js, React Three Fiber, drei | 0.187 · 9.8 · 10.7 | Facade pins on the site model |
| Maps | Google Maps JavaScript API (3D Maps, Routes), `@vis.gl/react-google-maps` | 1.10.2 | The site in 3D with its boundary, an orbit, and a drawn route; directions open in Google Maps |
| Quality | pytest, ruff, mypy strict, import-linter, ESLint | 9.2 · 0.17 · 2.4 · 2.16 | 153 backend tests; module boundaries checked in CI |
| Security | gitleaks, pip-audit, npm audit, Semgrep, Trivy, Argon2id | | Scans on every push; hashed passwords and session tokens |
| Ops | Docker Compose, Caddy, Sentry, structlog | 2.11.9 (Caddy) | One VM with automatic TLS, error reports, JSON logs |

Versions and alternatives are recorded in [docs/04-stack.md](docs/04-stack.md) and the [ADRs](docs/adr/).

## Architecture

A modular monolith: one deployable API split into eleven modules. Each module exposes one `api.py` that the others may import; inside, layers point inward (`interface → api → infrastructure → application → domain`). import-linter fails the build on any other import.

```mermaid
flowchart LR
  web[Next.js web app] -- REST + SSE --> api
  subgraph api[FastAPI modular monolith]
    direction TB
    agents --> capture & inspection & verification & stories & missions & passport
    mapping --> capture & sites & treatments
    inspection --> sites
    verification --> sites
  end
  api --> db[(Postgres + PostGIS + pgvector)]
  api --> s3[(Object store)]
  mapping -- DamageDetector --> claude[[Claude API]]
  mapping -- DamageDetector --> model[[Ready model over HTTP]]
  agents --> claude
  stories --> tts[[Azure Speech]]
```

| Module | Owns |
|---|---|
| `mapping` | wall maps and cells, rectification, grid, detector port, corrections, approval, accuracy |
| `treatments` | treatment catalog and plans scaled by damaged area |
| `agents` | the LangGraph run for each visitor photo |
| `capture` | uploads, EXIF strip, face blur, idempotency |
| `inspection` | quality gate, alignment, difference map, model judgment |
| `verification` | evidence rule, findings, expert reviews, claim checks |
| `stories`, `missions`, `passport` | sourced stories, photo missions for coverage gaps, anonymous passports |
| `sites` | region packs, sites, facades, baselines |
| `admin` | users, sessions, audit log, model cost counter |

## UML

All ten diagrams also live in [docs/11-uml.md](docs/11-uml.md). Click a title to expand.

<details>
<summary><b>Use cases</b>: Who uses Athar for what</summary>

```mermaid
flowchart LR
  visitor([Visitor])
  inspector([Inspector])
  expert([Conservation expert])
  admin([Admin])
  detector([Damage detector<br/>Claude or ready model])

  subgraph athar[Athar]
    uc1(Photograph a facade from a QR code)
    uc2(Hear the verified story)
    uc3(Collect passport stamps)
    uc4(Map a wall from one photo)
    uc5(View pins on the 3D site)
    uc6(Correct map cells)
    uc7(Approve a map)
    uc8(Read the treatment plan)
    uc9(Review uncertain findings)
    uc10(Track model accuracy)
    uc11(Watch cost per photo)
  end

  visitor --- uc1
  visitor --- uc2
  visitor --- uc3
  inspector --- uc4
  inspector --- uc5
  inspector --- uc8
  expert --- uc6
  expert --- uc7
  expert --- uc9
  expert --- uc10
  admin --- uc11
  uc4 -. calls .-> detector
  uc1 -. feeds .-> uc5
```

</details>

<details open>
<summary><b>Components</b>: Web app, API modules, stores and external services; arrows inside the API are the only imports allowed</summary>

```mermaid
flowchart TB
  subgraph web[Next.js web app]
    vpages[Visitor pages<br/>capture, observation, passport]
    dpages[Dashboard pages<br/>3D site, review, maps]
  end

  subgraph api[FastAPI modular monolith]
    agents[agents<br/>LangGraph run per photo]
    mapping[mapping<br/>rectify, grid, detector port]
    treatments[treatments<br/>catalog, plan]
    capture[capture<br/>EXIF strip, face blur]
    inspection[inspection<br/>align, diff, judge]
    verification[verification<br/>evidence rule]
    stories[stories]
    missions[missions]
    passport[passport]
    sites[sites<br/>region packs]
    admin[admin<br/>auth, audit, costs]
  end

  db[(Postgres<br/>PostGIS, pgvector)]
  s3[(Object store)]
  claude[[Claude API]]
  model[[Ready vision model<br/>over HTTP]]
  tts[[Azure Speech]]

  vpages -- REST + SSE --> agents
  dpages -- REST --> mapping
  dpages -- REST --> verification
  agents --> capture & inspection & verification & stories & missions & passport
  mapping --> capture & sites & treatments
  inspection --> sites
  verification --> sites
  api --> db
  api --> s3
  agents -- structured calls --> claude
  mapping -- detector port --> claude
  mapping -- detector port --> model
  stories --> tts
```

</details>

<details open>
<summary><b>Class diagram</b>: Domain of the wall map and the treatment plan</summary>

```mermaid
classDiagram
  direction LR
  class WallSize {
    +float width_m
    +float height_m
    +aspect() float
  }
  class Grid {
    +int rows
    +int cols
    +for_wall(wall, rows) Grid
    +parse(label) CellRef
    +coverage(box) dict
    +cell_area_m2(wall) float
  }
  class CellRef {
    +int row
    +int col
    +label() str
  }
  class Quad {
    +Point top_left
    +Point top_right
    +Point bottom_right
    +Point bottom_left
    +area() float
  }
  class MapCell {
    +CellRef ref
    +DamageType damage_type
    +Severity severity
    +ModelConfidence confidence
    +CellSource source
  }
  class CellCorrection {
    +CellRef ref
    +DamageType damage_type
    +Severity severity
  }
  class MapView {
    +UUID id
    +MapStatus status
    +DetectorStatus detector_status
    +MapCell[] cells
    +MapCell[] model_cells
  }
  class DamageDetector {
    <<interface>>
    +name str
    +detect(DetectionInput) DetectionOutput
  }
  class ClaudeGridDetector
  class HttpDetectionModel
  class HttpCellClassifier
  class ManualOnly
  class Catalog {
    +str version
    +ReviewStatus review_status
    +treatment_for(type, severity) Treatment
  }
  class Treatment {
    +str code
    +DamageType damage_type
    +Severity[] severities
    +str[] steps_ar
    +Material[] materials
    +bool specialist_required
  }
  class TreatmentPlan {
    +PlanItem[] items
    +DamagedArea[] unmatched
    +needs_specialist() bool
  }

  MapView "1" *-- "many" MapCell
  MapView --> Grid
  MapView --> WallSize
  MapView --> Quad
  MapCell --> CellRef
  CellCorrection --> CellRef
  Grid ..> CellRef : creates
  DamageDetector <|.. ClaudeGridDetector
  DamageDetector <|.. HttpDetectionModel
  DamageDetector <|.. HttpCellClassifier
  DamageDetector <|.. ManualOnly
  Catalog "1" *-- "many" Treatment
  TreatmentPlan ..> Catalog : built from
  TreatmentPlan ..> MapView : areas of
```

</details>

<details>
<summary><b>Sequence: visitor photo</b>: From upload to pin or expert review</summary>

```mermaid
sequenceDiagram
  actor Visitor
  participant Web as Visitor app
  participant API as agents
  participant Cap as capture
  participant Ins as inspection
  participant Ver as verification
  participant Sto as stories
  participant LLM as Claude

  Visitor->>Web: photo + consent
  Web->>API: POST /observations (Idempotency-Key)
  API->>Cap: strip EXIF, blur faces, store
  API-->>Web: 202 + events URL
  API->>Ins: identify facade, align to baseline, diff
  Ins->>LLM: judge numbered regions
  LLM-->>Ins: per-region verdicts
  API->>Ver: apply evidence rule
  alt confident
    Ver-->>API: publish pin (likely or confirmed)
  else unsure
    Ver-->>API: pause for expert
  end
  API->>Sto: story with sources
  API-->>Web: SSE status, story, stamp
```

</details>

<details>
<summary><b>Sequence: wall map</b>: From photo to approval</summary>

```mermaid
sequenceDiagram
  actor Inspector
  actor Expert
  participant Web as Dashboard
  participant Map as mapping
  participant Cap as capture
  participant Det as DamageDetector
  participant Tr as treatments
  participant DB as Postgres + store

  Inspector->>Web: wall, photo, four corners
  Web->>Map: POST /maps
  Map->>Cap: process_upload
  Map->>Map: rectify + draw grid
  Map->>Det: detect(rectified, labelled grid)
  alt detector answers
    Det-->>Map: cells, summary
  else detector down
    Det-->>Map: DetectorUnavailable
    Map->>Map: empty map, status failed
  end
  Map->>DB: map, cells, model_cells
  Map->>Tr: plan(areas by type and severity)
  Map-->>Web: map + plan + changes
  Expert->>Web: paint corrections
  Web->>Map: POST /maps/{id}/cells
  Expert->>Web: approve
  Web->>Map: POST /maps/{id}/approve
  Map->>DB: freeze, audit log
```

</details>

<details>
<summary><b>State: damage map</b>: Draft until an expert approves it</summary>

```mermaid
stateDiagram-v2
  direction LR
  state "Damage map" as map {
    [*] --> Draft: created
    Draft --> Draft: expert corrects cells
    Draft --> Approved: expert approves
    Approved --> [*]
  }
```

</details>

<details>
<summary><b>State: visitor observation</b>: Lifecycle of one visitor photo</summary>

```mermaid
stateDiagram-v2
  direction LR
  [*] --> received
  received --> processing
  processing --> needs_input: facade unclear
  needs_input --> processing: visitor answers or timeout
  processing --> needs_retake: blurry, dark, wrong angle
  processing --> done
  processing --> failed
  done --> [*]
  needs_retake --> [*]
  failed --> [*]
```

</details>

<details>
<summary><b>ER diagram</b>: Wall map tables and their neighbours</summary>

```mermaid
erDiagram
  SITES ||--o{ FACADES : has
  FACADES ||--o{ BASELINE_PHOTOS : has
  FACADES ||--o{ OBSERVATIONS : "photographed in"
  FACADES ||--o{ FINDINGS : "pinned on"
  FACADES ||--o{ DAMAGE_MAPS : "mapped in"
  DAMAGE_MAPS ||--o{ DAMAGE_MAP_CELLS : contains
  USERS ||--o{ DAMAGE_MAPS : "creates, approves"
  USERS ||--o{ AUDIT_LOG : writes

  DAMAGE_MAPS {
    uuid id PK
    uuid facade_id FK
    string wall_name
    float width_m
    float height_m
    int rows
    int cols
    jsonb corners
    string detector_status
    jsonb model_cells
    string status
  }
  DAMAGE_MAP_CELLS {
    uuid map_id PK
    int row PK
    int col PK
    string damage_type
    string severity
    string source
  }
  FINDINGS {
    uuid id PK
    string damage_type
    string severity
    string existence_label
    string status
  }
```

</details>

<details>
<summary><b>Deployment</b>: One VM with Docker Compose</summary>

```mermaid
flowchart LR
  phone[Phone browser] -- HTTPS --> caddy
  laptop[Inspector laptop] -- HTTPS --> caddy
  subgraph vm[One VM, Docker Compose]
    caddy[Caddy<br/>TLS]
    web[web<br/>Next.js standalone]
    api[api<br/>Uvicorn]
    db[(db<br/>Postgres 18)]
    storage[(storage<br/>SeaweedFS S3)]
  end
  caddy --> web
  caddy -- /api --> api
  api --> db
  api --> storage
  api -- HTTPS --> anthropic[[Anthropic API]]
  api -- HTTPS --> hf[[Model endpoint<br/>optional]]
  api -- HTTPS --> azure[[Azure Speech<br/>optional]]
```

</details>

<details>
<summary><b>Activity: expert review</b>: How a conservator checks and approves a map</summary>

```mermaid
flowchart TD
  start([Map opens]) --> look{Cells look right?}
  look -- yes --> approve[Approve]
  look -- no --> brush[Pick a damage type and severity]
  brush --> paint[Paint or erase cells]
  paint --> undo{Mistake?}
  undo -- yes --> back[Undo last stroke] --> paint
  undo -- no --> save[Save corrections]
  save --> look
  approve --> plan[Treatment plan and accuracy update]
  plan --> stop([Done])
```

</details>

## Run it

You need Docker with Compose v2.

```bash
cp .env.example .env          # add keys if you have them; it runs without
docker compose up --build     # first build takes a few minutes
```

| | URL |
|---|---|
| Visitor app | http://localhost:3000 |
| Dashboard | http://localhost:3000/dashboard |
| Wall damage maps | http://localhost:3000/dashboard/maps |
| API docs | http://localhost:8000/api/docs |

The `seed` service loads the demo region pack (`region-packs/demo`), a synthetic test building with four facades. It is not a heritage site. Create a dashboard account with:

```bash
docker compose run --rm -e SADU_NEW_USER_PASSWORD='choose-12-chars-or-more' api \
  python -m sadu.cli create-user inspector@example.com --role expert
```

Roles are `inspector`, `expert` (can also review) and `admin`. Test photos are in `region-packs/demo/test-photos/`.

For a public demo on a VM, set `SADU_DOMAIN` and `SADU_ENV=prod` in `.env`, then `docker compose --profile prod up -d`. Caddy gets TLS certificates and serves the app on 443.

## Environment

| Variable | Needed for | Without it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Damage judgment, wall maps with `claude`, story drafting, claim checks | Changes go to the expert queue unjudged; maps are saved empty for manual labelling |
| `SADU_DAMAGE_DETECTOR` | `claude` (default), `http_detection`, `http_cell_classification` or `none` | `claude` |
| `SADU_DETECTOR_URL`, `SADU_DETECTOR_TOKEN`, `SADU_DETECTOR_LABELS` | A ready model behind HTTP, its token, and a JSON map from model labels to damage types | Required for the two `http_*` detectors |
| `SADU_DETECTOR_MIN_SCORE`, `SADU_MAP_ROWS` | Drop weaker predictions (default 0.35); grid rows (default 8) | Defaults |
| `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | Arabic audio (`ar-SA-HamedNeural`) | Story shows as text only |
| `SADU_DEMO_MODE` | `true` serves recorded model answers before calling the API | Live calls; recordings are still used if a call fails |
| `SADU_DAILY_LLM_BUDGET_USD` | Daily spend cap, default 10 | Calls past the cap fail over to the fallbacks |
| `GOOGLE_MAPS_API_KEY` | 3D site view and in-app routes (Maps JavaScript API with Map Tiles and Routes enabled; restrict it to your domain) | Visitors see the facade model; the Google Maps directions link still works |
| `SENTRY_DSN_API` | Error reports | Errors are only in the logs |
| `POSTGRES_PASSWORD`, `S3_*` | Change for anything public | Dev defaults |
| `SADU_DOMAIN` | Production profile | `localhost` |

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

Score a damage detector on labelled wall photos before the demo:

```bash
uv run python -m eval.score_maps ../path/to/walls --min-accuracy 0.8
```

The folder format is in [docs/10-damage-maps.md](docs/10-damage-maps.md).

Frontend, from `frontend/`:

```bash
npm ci
npm run lint && npm run typecheck && npm run build
```

CI runs all of the above plus `pip-audit`, `npm audit`, gitleaks, Semgrep, Trivy and a render of every Mermaid diagram in `docs/`.

## Project layout

```
backend/                   FastAPI modular monolith (Python 3.13, uv)
  src/sadu/modules/        sites, capture, inspection, verification, stories, missions,
                           passport, agents, admin, mapping, treatments
    <module>/api.py        the only file other modules import
    <module>/domain/       pure rules, no framework imports
    <module>/application/  use cases and ports (DamageDetector)
    <module>/infrastructure/  ORM, OpenCV, HTTP clients
    <module>/interface/    FastAPI routes and schemas
  src/sadu/shared/         config, database, storage, ports and adapters
  alembic/                 migrations
  tests/                   unit and integration tests
  eval/                    vision and wall map evaluation
frontend/src/
  app/<page>/page.tsx      thin route file
  app/<page>/_components/  components only that page uses
  components/              shared by two or more pages
  lib/                     API clients, labels, palette, plurals
infra/                     database image, storage start script, Caddyfile
region-packs/demo/         synthetic demo building, baselines, test photos, sources
region-packs/treatments/   treatment catalog for earthen walls (draft)
docs/                      scope, research, architecture, ADRs, UML, threat model
```

## Documentation

| Topic | File |
|---|---|
| Scope and requirements | [docs/00-scope.md](docs/00-scope.md) |
| Research and market comparison | [docs/01-research.md](docs/01-research.md) |
| Architecture, API contract, data | [docs/03-architecture.md](docs/03-architecture.md) |
| Stack and versions | [docs/04-stack.md](docs/04-stack.md) |
| Security and threat model | [docs/06-security/threat-model.md](docs/06-security/threat-model.md) |
| Verification and demo script | [docs/09-verification-and-demo.md](docs/09-verification-and-demo.md) |
| Wall damage maps | [docs/10-damage-maps.md](docs/10-damage-maps.md) |
| UML and structure | [docs/11-uml.md](docs/11-uml.md) |
| Decisions (ADR-001 to ADR-022) | [docs/adr/](docs/adr/) |

## Privacy

Faces are blurred and EXIF removed before any photo is stored or sent to a model. Location is used only with consent and discarded once the facade is known. Visitor photos are kept 30 days unless they are evidence for a published finding, and a visitor can delete their passport and every non-evidence photo from the passport page. See [the threat model](docs/06-security/threat-model.md).
