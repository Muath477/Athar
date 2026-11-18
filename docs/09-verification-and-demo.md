# 09 · Verification and demo script

## 1. Verification evidence (2026-11-16, branch `stage8-build`)

| Check | Result | How to repeat |
|---|---|---|
| Backend tests | 93 passed (unit and integration, against PostGIS + pgvector) | `uv run pytest` (see README) |
| Lint, format, types | ruff, ruff format, mypy strict: no issues in 120 files | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |
| Module boundaries | 3 import-linter contracts kept | `uv run lint-imports` |
| Migrations | `alembic upgrade head` on an empty database, then `alembic check`: no drift | CI step "Migrate the test database" |
| Vision evaluation | facade identification 4/4, damage recall 1/1, no false damage on unchanged facades 2/2, shadow flagged as lighting 1/1, off-target photo sent to retake 1/1, slowest photo about 1.5 s | `uv run python -m eval.run` |
| Frontend | eslint, `tsc --noEmit` and `next build` pass | `npm run lint && npm run typecheck && npm run build` |
| End to end in Docker | Photo uploaded through the web proxy, run to completion with no API key: the change went to the expert queue with its evidence and the passport was stamped | `docker compose up --build`, upload `north-crack.jpg` |
| Screens | Home, capture, result, passport, dashboard 3D model, review queue with baseline / aligned / difference evidence checked in Playwright screenshots | manual |
| Dependencies | pip-audit: no known vulnerabilities; Trivy on lockfiles: 0 high or critical | CI `backend` and `security` jobs |
| Secrets | gitleaks over full history: no leaks | CI `security` job |
| Container config | Trivy misconfiguration scan: 0 high or critical after the database image moved to a non-root user | CI `security` job |
| Diagrams | All 10 Mermaid diagrams render with mermaid-cli 12.0.1 | CI `docs` job |

Not yet verified:

- The live Claude path (judgment, plan, story drafting, claim checks) runs only with recorded answers in tests. It needs one run with a real key before the demo.
- Azure audio needs a real key.
- Semgrep could not reach its rule registry from the build sandbox; it runs in CI.
- The evaluation set is four synthetic photos. Thresholds must be re-checked on the real baselines.
- First CI run on GitHub: pending.

## 2. Three-minute demo script

Roles: **Speaker** (pitch), **Phone** (visitor), **Laptop** (dashboard, logged in as expert). Demo mode on, recordings made the day before.

### 0:00 – 0:30 · The weave

Speaker, with a photo of a Sadu weave on screen:

> السدو نسيج تصنعه نساء البادية من خيوط كثيرة، كل خيط وحده ضعيف، ومع بعضها تصير قطعة تشيل بيت كامل. في 2020 دخل السدو قائمة اليونسكو للتراث الثقافي غير المادي، ملفًا مشتركًا بين السعودية والكويت.
>
> مبانينا الطينية تحتاج الشي نفسه. ما فيه مفتش يقدر يزور كل واجهة كل أسبوع، لكن آلاف الزوار يصورونها كل يوم. سدو يحوّل صورهم إلى خيوط، وينسجها في صورة وحدة حيّة لحالة الموقع.

Source for the inscription: [UNESCO, Traditional weaving of Al Sadu](https://ich.unesco.org/en/RL/01586), decision 15.COM 8.B.4.

### 0:30 – 1:20 · The visitor

Phone, screen mirrored:

1. Open Athar, tap "صوّر الواجهة", allow location. (5 s)
2. Photograph the north facade (`north-crack.jpg` printed, or the real wall). Progress shows each agent step: نتعرّف على الواجهة، نقارن صورتك بالصورة المرجعية، نتحقق من النتائج. (20 s)
3. The story appears with a label on each sentence (موثّق، رواية شفهية، تفسير) and plays in a Saudi voice. (15 s)
4. Open the passport: a new stamp. (5 s)

Speaker:

> الزائر ما يكتب بلاغ ولا يعرف شي عن الترميم. يصوّر، ويطلع له قصة موثّقة، وكل جملة فيها مربوطة بمصدرها.

### 1:20 – 2:20 · The authority

Laptop:

1. Review queue: the new crack waits for an expert because the model was not sure enough to publish alone. Show its evidence: baseline, aligned photo, difference map and the agent's Arabic rationale. (20 s)
2. Confirm it as expert. (5 s)
3. Dashboard: the 3D model now has a pin on the north facade. Click it: label مؤكد, severity, date, evidence. (20 s)
4. Show the shadow photo's result: treated as lighting, nothing published. (15 s)

If the model publishes the crack directly as مرجح, skip steps 1 and 2 and start from the pin.

Speaker:

> ما يوصل للوحة شي بدون دليل: صورة الأساس، الصورة الجديدة، وخريطة الفرق. إذا الذكاء الاصطناعي متردد، يروح الموضوع لخبير. وإذا الصورة ظل أو زاوية غلط، نطلب من الزائر يعيد التصوير.

### 2:20 – 2:50 · Why it holds up

Speaker, one slide:

- Five agents, each with one job, and a fixed rule decides what gets published.
- Every external call has a timeout and a fallback; without the model, changes still reach an expert.
- Faces blurred and location dropped before anything is stored; a visitor can delete everything.
- Cost per photo shown live from the cost counter.

### 2:50 – 3:00 · Close

> كل زائر خيط. سدو ينسجهم.

### If something fails on stage

| Failure | Do this |
|---|---|
| Venue Wi-Fi down | Phone on mobile data; demo mode serves recorded answers |
| Camera or location blocked | Upload the printed test photo from the gallery |
| Audio does not play | Read the story text; it is shown on screen |
| Anything else | Play the backup screen recording |
