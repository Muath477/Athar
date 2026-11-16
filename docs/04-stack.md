# 04 · Tech stack confirmation

Versions checked on **2026-11-16** against the PyPI and npm registries and Docker Hub (latest published), and API usage spot-checked in current docs via Context7 and Microsoft Learn. "Pin" is the version to install at build time; re-check patch releases on Nov 17. Anything not verified is marked TBD.

## Backend and agents

| Need | Choice | Pin | Why it fits | Main alternative | Trade-off |
|---|---|---|---|---|---|
| Language | Python | 3.13 (`python:3.13-slim`, 3.13.13 available) | Best CV + LLM ecosystem; all libraries below support it | TypeScript end to end | Two languages in the repo |
| Lint/format/types | ruff, mypy | 0.17.5 / 2.4.1 | Fast, one config | flake8 + black + pyright | none significant |
| API | FastAPI + Pydantic + Uvicorn | 0.163.1 / 2.14.3 / 0.54.0 | Typed schemas, OpenAPI generated, async | Django + DRF | Fewer batteries (we add auth ourselves) |
| Settings | pydantic-settings | 2.16.3 | Env-based config with validation | dynaconf | none |
| SSE | sse-starlette | 3.7.0 | Simple SSE for status | WebSockets | One-way only, which is all we need |
| Agent orchestration | LangGraph + langchain-core + checkpoint-postgres | 1.2.22 / 1.8.1 / 3.2.1 | Graph state, interrupts, Postgres persistence ([ADR-002](adr/ADR-002-langgraph-orchestration.md)) | Hand-written state machine | Dependency weight; re-run semantics on resume |
| LLM | Anthropic SDK; `claude-sonnet-5-5`, `claude-haiku-5-5` | anthropic 2.9.0 | Vision + structured outputs + Arabic ([ADR-003](adr/ADR-003-llm-claude.md)) | Other hosted VLMs behind the port | Data leaves the Kingdom (PDPL question) |
| ORM / migrations / driver | SQLAlchemy, GeoAlchemy2, Alembic, psycopg | 2.1.8 / 0.21.0 / 1.20.1 / 3.3.9 | Mature, typed 2.x API, spatial types | SQLModel | More boilerplate |
| Vector client | pgvector (Python) | 0.5.1 | SQLAlchemy `Vector` type | raw SQL | none |
| Module boundaries | import-linter | 2.16 | Enforces ADR-001 in CI | code review only | none |
| Password hashing | argon2-cffi | 25.1.0 | Argon2id | bcrypt | none |
| Object storage client | boto3 | 1.44.3 | Any S3 endpoint | aioboto3 | Sync calls run in a thread pool |
| Background jobs | FastAPI BackgroundTasks | with FastAPI | No extra infra ([ADR-008](adr/ADR-008-background-jobs.md)) | Arq/Celery + Redis | No multi-process scaling |
| PDF (Round 2) | WeasyPrint | 70.0 | HTML/CSS to PDF with RTL | headless Chromium print | System libs (Pango) in the image |
| Rate limiting | in-house token bucket in `shared/rate_limit.py` | n/a | One process, ~40 lines, no stale dependency (slowapi's last release is 0.1.10) | slowapi | We own the code |
| Logging | structlog | 26.1.0 | JSON logs with context | stdlib logging | none |

## Computer vision

| Need | Choice | Pin | Why | Alternative | Trade-off |
|---|---|---|---|---|---|
| Alignment, normalization, difference | opencv-python-headless | 5.0.0.93 | SIFT, MAGSAC homography, CLAHE in one package | kornia | CPU only, fine at demo volume |
| SSIM | scikit-image | 0.26.0 | `structural_similarity(full=True)` | own implementation | Extra dependency |
| Damage judgment | Claude Sonnet 5.5 | see above | No training needed | trained segmentation | Cost per call |
| Optional segmentation | Ultralytics YOLO seg (pretrained) | 8.4.215 | Quick masks | none needed in R1 | **AGPL-3.0**; pulls PyTorch; off by default |
| Face blurring | OpenCV `FaceDetectorYN` + YuNet ONNX | `face_detection_yunet_2023mar.onnx` (338 KB, from opencv_zoo) | Small, fast, CPU | MediaPipe | Model file is downloaded at image build, not bundled in the wheel |
| Imaging I/O | Pillow, numpy | 13.0.0 / 2.5.5 | EXIF handling, arrays | n/a | none |

## Data and retrieval

| Need | Choice | Pin | Why | Alternative | Trade-off |
|---|---|---|---|---|---|
| Database | PostgreSQL | 18.7 | One store for all ([ADR-004](adr/ADR-004-postgres-postgis-pgvector.md)) | managed Postgres | We run backups |
| Spatial | PostGIS | 3.7 (image `postgis/postgis:18-3.7`) | GPS → site, distances | app-side geometry | Brief said 3.6.x; 3.7 is current |
| Vectors | pgvector | 0.8.7 | HNSW index | dedicated vector DB | none at this size |
| Embeddings | BGE-M3 via FlagEmbedding | 1.4.2; model `BAAI/bge-m3` (TBD verify on Hugging Face) | Strong multilingual incl. Arabic, no API key ([ADR-009](adr/ADR-009-embeddings.md)) | hosted embeddings API | ~2 GB in the image |
| Object storage | S3 API; SeaweedFS locally | image tag pinned at build (TBD) | `minio/minio` not found on Docker Hub on 2026-11-16 ([ADR-006](adr/ADR-006-object-storage.md)) | Garage | New tool for the team |

## Frontend

| Need | Choice | Pin | Why | Alternative | Trade-off |
|---|---|---|---|---|---|
| Framework | Next.js App Router + React + TypeScript strict | 16.4.6 / 19.3.1 / TBD (pin what create-next-app ships; npm latest is 7.0.2) | SSR first screen, one app ([ADR-012](adr/ADR-012-frontend.md)) | Vite SPA | Bundle discipline needed |
| Runtime | Node.js | `node:24-alpine` (Next requires >= 20.9.0) | LTS line | Bun | none |
| Styling | Tailwind CSS | 4.3.5 | Logical utilities (`ms-*`, `me-*`, `ps-*`) for RTL | CSS modules | Learning curve for v4 config |
| Lint | eslint + eslint-config-next | 10.15.0 / 16.4.6 | Next rules | Biome | none |
| PWA | Web App Manifest + small service worker | n/a | Install-free | next-pwa plugins | We write ~50 lines |
| 3D | three, @react-three/fiber, @react-three/drei | 0.187.0 / 9.8.2 / 10.7.9 | GLB + Draco, pointer events ([ADR-007](adr/ADR-007-3d-twin.md)) | Babylon.js | none |
| 3D compression | @gltf-transform/cli | 4.5.1 | Draco + KTX2 | Blender exporters | none |
| Splats (optional) | @sparkjsdev/spark | 2.4.0 | Only if the scan is a splat | mesh only | Extra code path |
| National map (R2) | MapLibre GL JS | 6.18.0 | No token | Leaflet | Needs a tile source (TBD) |
| Arabic TTS | Azure AI Speech, `ar-SA-HamedNeural` / `ar-SA-ZariyahNeural` | REST API ([ADR-016](adr/ADR-016-build-time-changes.md)) | Saudi voices confirmed in docs ([ADR-010](adr/ADR-010-tts.md)) | Google TTS | Azure key and region |

## Quality, security, operations

| Need | Choice | Pin |
|---|---|---|
| Tests | pytest; Playwright | 9.2.0 / @playwright/test 1.65.1 |
| LLM tracing | `llm_calls` table (Langfuse dropped, [ADR-016](adr/ADR-016-build-time-changes.md)) | none |
| Errors | Sentry | sentry-sdk 2.75.0; @sentry/nextjs 11.13.0 |
| Security scans | gitleaks, pip-audit, npm audit, Trivy, Semgrep | pip-audit 2.10.1, semgrep 1.185.0; gitleaks and Trivy GitHub Actions pinned by commit SHA at setup (TBD) |
| Diagrams check | @mermaid-js/mermaid-cli | 12.2.0 |
| Containers | Docker multi-stage + compose | current stable |
| Reverse proxy | Caddy | 2.11.9 |
| CI | GitHub Actions | repo TBD |

## Cost per photo

Estimate, to be replaced by the measured counter (`GET /admin/costs`). Prices: Sonnet 5.5 USD 2 / 10 per million input/output tokens; Haiku 5.5 USD 0.10 / 0.50 (Anthropic first-party rates as of 2026-11-03).

| Step | Model | Input tokens | Output tokens (incl. thinking) | Cost (USD) |
|---|---|---|---|---|
| Plan | Haiku | ~1,500 | ~200 | 0.0003 |
| Facade tie-break (about 1 in 4 photos) | Haiku | ~4,000 | ~200 | 0.0001 amortized |
| Damage judgment (3 images ~1,600-2,600 tokens each + prompt) | Sonnet | ~10,000 | ~1,500 | 0.035 |
| Story (cached per site/facade, amortized) | Sonnet + Haiku | n/a | n/a | ~0 |
| TTS (cached) | Azure | n/a | n/a | ~0 |
| **Total** | | | | **~0.035** (target <= 0.05) |

Levers if the measured cost is higher: lower image size to 1,024 px for judgment, skip judgment when the difference map has no region (no change → no LLM call), prompt caching of the fixed system prompt.

## Context7 / docs checks done

- LangGraph: `interrupt()` + `Command(resume=...)` need a checkpointer; the node re-executes from its start on resume.
- Anthropic Python SDK: structured output via `output_config={"format": {"type": "json_schema", "schema": ...}}` or `messages.parse(output_format=Model)`; `temperature` and `output_format` dicts removed.
- OpenCV 5.0: `FaceDetectorYN` with `face_detection_yunet_2023mar.onnx`.
- Azure AI Speech: `ar-SA-HamedNeural`, `ar-SA-ZariyahNeural` exist.

Still to check at build time (TBD): drei `useGLTF` + KTX2 loader wiring; SeaweedFS S3 config flags; pgvector apt package name for PG 18 on the PostGIS image; Next 16 service worker conventions; Tailwind 4 RTL utilities.
