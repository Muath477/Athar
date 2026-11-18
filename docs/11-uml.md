# 11 · UML and structure

Written 2026-11-18. One diagram per question a reviewer asks. All diagrams are Mermaid and render on GitHub; CI renders them with mermaid-cli on each push.

## 1. Who uses Athar for what (use cases)

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

## 2. Components and the boundaries between them

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

Arrows inside the API are allowed imports. import-linter fails the build on any other direction.

## 3. Domain classes of the wall map

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

## 4. A visitor photo, end to end

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

## 5. A wall map, from photo to approval

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

## 6. Lifecycles

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

## 7. Data (wall map tables and their neighbours)

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

## 8. Deployment

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

## 9. Expert review of a map (activity)

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

## 10. Folder structure

```
backend/src/sadu/
  main.py                    app, routers, lifespan (detector built here)
  shared/                    config, db, errors, i18n, storage, ports (llm, speech), adapters
  modules/<module>/
    api.py                   the only thing other modules import
    domain/                  pure rules, no framework imports
    application/             use cases and ports (DamageDetector lives here)
    infrastructure/          ORM, OpenCV, HTTP clients
    interface/               FastAPI routes and schemas
frontend/src/
  app/<page>/page.tsx        thin route file
  app/<page>/_components/    components only that page uses
  components/                components shared by two or more pages
  lib/                       API clients, labels, palette, hooks
region-packs/
  demo/                      sites, facades, baselines, test photos
  riyadh/                    eleven Riyadh-region heritage sites, sample satellite events
  treatments/                treatment catalog (draft)
docs/                        scope, research, architecture, ADRs, UML
```

## 11. A satellite alert, from orbit to the wall

```mermaid
sequenceDiagram
  autonumber
  participant Cron as Scan schedule
  participant Watch as watch module
  participant STAC as Earth Search STAC
  participant COG as Sentinel-2 COGs (S3)
  participant DB as Postgres
  actor Inspector
  participant Missions as missions module
  actor Visitor

  Cron->>Watch: due_sites(7 days)
  Watch->>STAC: search sentinel-2-c1-l2a over the site, cloud < 40 %
  STAC-->>Watch: items with asset hrefs
  Watch->>COG: windowed GTiff reads, 6 bands + SCL
  Watch->>Watch: median composites, z-score change, classify, score
  Watch->>DB: site_scans row + before/after/change PNGs
  Inspector->>Watch: open /dashboard/watch, pick the site
  Inspector->>Watch: POST /watch/scans/{id}/ground-check
  alt the site has facades
    Watch->>Missions: create_mission(facade, satellite_alert) x up to 3
    Missions-->>Visitor: high-priority photo mission nearby
    Visitor->>Missions: photo of the facade
  else no facades yet
    Watch-->>Inspector: inspector visit needed
  end
```
