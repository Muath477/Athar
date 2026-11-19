<div align="center">

# أثر — Athar

[![CI](https://github.com/Muath477/Athar/actions/workflows/ci.yml/badge.svg)](https://github.com/Muath477/Athar/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.13-1f1a16?logo=python&logoColor=efe4d2)
![FastAPI](https://img.shields.io/badge/FastAPI-0.163-1f1a16?logo=fastapi&logoColor=efe4d2)
![Next.js](https://img.shields.io/badge/Next.js-16-1f1a16?logo=nextdotjs&logoColor=efe4d2)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18%20%2B%20PostGIS-1f1a16?logo=postgresql&logoColor=efe4d2)
![Docker](https://img.shields.io/badge/Docker-Compose-1f1a16?logo=docker&logoColor=efe4d2)

</div>

<div dir="rtl">

**أثر** منصة عربية تساعد جهات التراث على متابعة حالة الجدران الطينية من الأرض ومن الفضاء. تصل صور الجدار من المساح الميداني أو كاميرات الموقع أو الطائرات المسيّرة أو الرفع الجماعي، فتُطمس الوجوه وتُحذف بيانات الموقع من الصورة قبل حفظها، ثم يقترح نموذج التحليل مخطط تلف أوليًا بمصطلحات المسرد الموحد. يراجع أخصائي الترميم المخطط ويصححه، ولا يُعتمد إلا بعد فحص ميداني موثّق، وتخرج منه خطة معالجة بالمواد والكميات وتقارير PDF وCSV. ومن الفضاء، يفحص أثر محيط كل موقع أسبوعيًا بصور Sentinel-2، فينبّه إلى البناء الجديد والحفر وتجمّع المياه، ويفتح مهام تصوير ميدانية للتحقق على الأرض.

</div>

**Athar** is an Arabic-first platform that helps heritage authorities follow the condition of mud-brick walls from the ground and from space. Wall photos arrive from field surveyors, site cameras, drones and bulk uploads. Faces are blurred and location data stripped before anything is stored, then an analysis model drafts a damage map in the unified glossary. A conservation specialist corrects the draft, and it can be approved only after a recorded field inspection. The approved map carries a treatment plan with materials and quantities, and downloads as PDF and CSV. From orbit, Athar screens the surroundings of each site weekly with Sentinel-2, warns about new building, digging and standing water, and opens photo missions so someone checks on the ground.

**العرض المسجّل · Demo video:** [شاهده في المتصفح · watch in the browser](https://cdn.jsdelivr.net/gh/Muath477/Athar@8aeb515757ed07a351baa5f1db5930a218e2eb3f/docs/demo/athar-demo.mp4) · [الملف · file](docs/demo/athar-demo.mp4) (دقيقتان، يمرّ على الرصد من الفضاء، مخطط الجدار، الفحص الميداني والاعتماد، الكاميرات، الرفع الجماعي، مساعد أثر، الصلاحيات وسجل التدقيق).

<p align="center"><img src="docs/assets/athar-pipeline.svg" alt="Animated pipeline: a wall photo has faces blurred, is straightened and split into a grid, damaged cells are marked and corrected by an expert, and a treatment plan with materials appears" width="100%"></p>

## Challenges it answers

Built by team Athar for the agentX Riyadh hackathon, Culture and Heritage track.

| Challenge owner | Challenge | Where Athar answers it |
|---|---|---|
| Diriyah Gate Development Authority (هيئة تطوير بوابة الدرعية) | Detecting and mapping damage to mud walls | Wall damage maps, the ten-step workflow, specialist correction and approval, treatment plans ([ADR-017](docs/adr/ADR-017-diriyah-challenge-alignment.md), [ADR-026](docs/adr/ADR-026-diriyah-agent-workflow.md)) |
| Heritage Commission (هيئة التراث) | «كيف نرى التراث من الفضاء؟» | Weekly Sentinel-2 screening of eleven Riyadh-region sites, early warning and ground checks ([ADR-025](docs/adr/ADR-025-space-watch.md)) |

## Who pays, and why visitors take part

<div dir="rtl">

- **من يدفع:** الجهة المسؤولة عن الموقع (هيئة تطوير بوابة الدرعية، هيئة التراث، أو أمانة المنطقة)، باشتراك سنوي لكل موقع مرصود يُضاف على شكل حزم مناطق. يشمل الاشتراك الرصد من الفضاء، ومخططات التلف، والتقارير، ومساعد أثر، وسجل التدقيق.
- **ما يتحمله أثر في كل صورة:** صور Sentinel-2 مجانية ومفتوحة. التكلفة المتغيرة هي استدعاءات النموذج المستضاف، ويسجلها أثر لكل استدعاء ويحسب تكلفة الصورة الواحدة لمسؤول النظام (`GET /api/v1/admin/costs`). نموذجنا Qwen3.5 على جهاز الجهة يُخفّض هذه التكلفة ويبقي الصور داخل المملكة.
- **لماذا يصوّر الزائر:** لا يدفع شيئًا. يحصل على قصة المكان بمصادرها وصوت عربي، وختم في جوازه، فتأتي المراقبة مع الزيارة. كل صورة منه زيارة كانت الجهة سترسل لها فريقًا.
- **ما لم يثبت بعد:** لم توافق أي جهة على الدفع حتى الآن، ولم نقس التكلفة الفعلية لكل صورة بنموذج حقيقي، فالعرض يستخدم إجابات مخزّنة.

</div>

- **Customer:** the authority responsible for the site (Diriyah Gate Development Authority, the Heritage Commission, or a regional municipality), on a yearly subscription per monitored site, sold as region packs. It covers space watch, damage maps, reports, the assistant and the audit trail.
- **Cost per photo:** Sentinel-2 imagery is free and open. The variable cost is hosted model calls, which Athar records per call and turns into a cost per photo for the admin (`GET /api/v1/admin/costs`). Our own Qwen3.5 model on the authority's machine lowers that cost and keeps photos in the country.
- **Why visitors take part:** they pay nothing. They get a sourced story of the place with Arabic audio and a passport stamp, so monitoring comes with the visit. Each visitor photo is a visit the authority would otherwise send a team for.
- **Not proven yet:** no authority has agreed to pay, and the real cost per photo has not been measured with a live model; the demo uses cached answers.

## Success metrics

| Metric | Target | How it is measured | Status on 2026-11-19 |
|---|---|---|---|
| Every report that reaches the dashboard has evidence | 100% | `python -m sadu.cli quality`, `GET /api/v1/reports/quality`, the card on `/dashboard/audit` | Enforced by a database constraint for visitor findings. The demo data shows 13 of 17 approved maps: the other 4 were approved before the field inspection became mandatory, and the report flags them. |
| Damage recall and precision on real walls | Recall ≥ 0.70 for cracks and plaster loss, precision ≥ 0.60 | `eval.score_maps` on walls a specialist drew first; the accuracy card on approved maps | Not measured on real walls yet. Two independent LoRA runs on public crack photos (not Athar walls) both moved crack F1 to about 0.95 (0.629→0.951, then 0.608→0.945) — see [ADR-029](docs/adr/ADR-029-own-model.md) — which is evidence the training method is reproducible, not a wall-level score. The fetch bug that kept the plaster-loss and salt-efflorescence sources unreachable is now fixed. |
| Photo attributed to the right facade | ≥ 90% | `eval.run` on the demo pack; GPS facade matching tests | 4 of 4 on synthetic photos only |
| False or unclear reports stopped before the dashboard | ≥ 9 of 10 | `eval.run` (shadows, off-target photos); live share of photos sent back and findings held for a specialist in the quality report | 2 of 2 on synthetic photos only |
| Story claims without a source | Fewer with the verifier than without | A set of drafted claims checked with and without the claims verifier | Not measured yet |

## What works today

<div dir="rtl">

- مخطط تلف من صورة واحدة: تحديد زوايا الجدار الأربع، ثم تقويم الصورة وتقسيمها إلى شبكة، ثم رسم عناصر التلف بمصطلحات المسرد الموحد.
- مسار هيئة تطوير بوابة الدرعية بخطواته العشر، وتصحيحات المختص مع سجلها، والفحص الميداني شرطًا للاعتماد.
- خطة معالجة من مكتبة المعالجات (مسودة)، وتقرير الجدار PDF، وجدول العناصر CSV، وتقرير حالة الموقع PDF وCSV.
- رصد أسبوعي من الفضاء لأحد عشر موقعًا في منطقة الرياض، مع ترتيب المخاطر وإنذار مبكر وتنبيهات عبر Webhook.
- استقبال الصور من الكاميرات والطائرات المسيّرة والرفع الجماعي، ومطابقة الصورة بالواجهة من إحداثياتها.
- «مساعد أثر» للموظفين بخمس مهارات فحص، يصوغ ملف تدقيق PDF ولا يرسله إلا بعد تأكيد المستخدم.
- ستة أدوار، وتقييد الحساب بمواقع محددة، وسجل تدقيق قابل للتنزيل، وحذف تلقائي لصور الزوار بعد ٣٠ يومًا.
- تقرير جودة يجيب عن سؤال: هل وصل شيء إلى اللوحة بلا دليل؟ ويعرض الصور المعادة لأصحابها وما حُجز للمختص وما صححه.
- تطبيق الزائر: يصوّر الواجهة بمطابقة الصورة المرجعية، ويسمع قصة المكان بمصادرها، ويحصل على ختم في جوازه.

</div>

- One photo becomes a wall damage map: four corners, rectification, a grid, and elements in the unified glossary.
- The ten-step Diriyah workflow, specialist corrections with a correction log, and a field inspection before approval.
- Treatment plans from a draft catalog, the wall report PDF, the elements CSV, and the site condition PDF and CSV.
- Weekly satellite screening of eleven Riyadh-region sites with risk ranking, early warning and webhook alerts.
- Photos from site cameras (HTTP snapshot), drones and bulk uploads, matched to a facade by GPS.
- «مساعد أثر», a staff assistant with five inspection skills that drafts an audit PDF and sends it only after the user confirms.
- Six roles, site scoping, an exportable audit log, and a 30-day purge of visitor photos.
- A quality report that answers "did anything reach the dashboard without evidence?", plus photos sent back, findings held for a specialist and maps the specialist corrected.
- The visitor app: photograph a facade, hear a sourced story, collect a passport stamp, see the site in 3D with directions.
- The code path for Athar's own damage model: dataset builder, Colab notebook, evaluation, model registry and detector.

## Roadmap

- Train the own model once enough maps are approved, and switch to it only when it beats the active detector on the same test maps ([ADR-029](docs/adr/ADR-029-own-model.md)).
- Measure accuracy on real Najdi walls against specialists, and have a conservator review the treatment catalog.
- Ship `ffmpeg` in the API image so RTSP-only cameras work.
- Add a lease to the schedulers so more than one API process can run.
- Read text from PDFs attached to the assistant (with OCR for scanned reports).
- Scope visitor findings and pins by site, for a pilot with several authorities.
- Measure unsourced story claims with and without the claims verifier.
- Interview the challenge owners for inspection frequency and late-found damage, and test the subscription model with one authority.

## Contents

- [How it flows](#how-it-flows)
- [Features by role](#features-by-role)
- [Identity and interface](#identity-and-interface)
- [Wall damage maps and the glossary](#wall-damage-maps-and-the-glossary)
- [Workflow and approval](#workflow-and-approval)
- [Satellite watch and early warning](#satellite-watch-and-early-warning)
- [Cameras, drones and bulk upload](#cameras-drones-and-bulk-upload)
- [The assistant](#the-assistant)
- [Athar's own model](#athars-own-model)
- [Governance](#governance)
- [Privacy and PDPL](#privacy-and-pdpl)
- [Visitors](#visitors)
- [Architecture](#architecture)
- [Running it](#running-it)
- [Environment variables](#environment-variables)
- [Testing and quality](#testing-and-quality)
- [Documentation](#documentation)
- [Limitations](#limitations)

## How it flows

Every wall photo, whatever its source, ends in the same draft map and the same specialist approval. The model only drafts; a specialist approves. Visitor photos take their own path through the visitor agents to the specialist's review queue.

```mermaid
flowchart TD
  sat["Satellite watch<br/>weekly Sentinel-2 screen"] -->|alert| missions["Photo missions<br/>ground check"]
  missions --> visitor["Visitor photo"]
  missions --> inspector["Inspector photo<br/>four wall corners"]
  camera["Site camera"] --> ingest["Ingest job<br/>GPS match to facade"]
  drone["Drone survey"] --> ingest
  upload["Bulk upload"] --> ingest
  inspector --> privacy["Face blur and EXIF strip"]
  ingest --> privacy
  privacy --> detector{"Analysis model"}
  detector -->|claude| grid["Hosted grid detector"]
  detector -->|qwen| own["Own Qwen3.5 model"]
  grid --> draft["Draft wall map"]
  own --> draft
  draft --> workflow["Ten-step workflow"]
  workflow --> corrections["Specialist corrections"]
  corrections --> field["Field inspection"]
  field --> approval["Approval"]
  approval --> plan["Treatment plan"]
  plan --> reports["PDF and CSV reports"]
  draft -->|urgent elements| notices["Notifications<br/>webhook"]
  workflow -->|overdue approval| notices
  sat -->|alert| notices
  visitor --> agents["Visitor agents<br/>blur, compare with baseline"]
  agents --> queue["Specialist review queue"]
  staff["Staff in the assistant"] --> skill["Inspection skill"]
  skill -->|analyse_photo| detector
  skill --> audit["Audit file PDF"]
  audit -->|user confirms| notices
```

The other detectors (`http_detection`, `http_cell_classification`, `none`) plug into the same place; see [ADR-018](docs/adr/ADR-018-damage-detector-port.md).

## Features by role

Permissions come from `ROLE_PERMISSIONS` in [`backend/src/sadu/modules/admin/api.py`](backend/src/sadu/modules/admin/api.py). The dashboard reads the same matrix from `GET /api/v1/auth/roles`, hides what a role cannot open, and the API refuses it anyway.

| Role | Permissions | Screens |
|---|---|---|
| المساح الميداني · `inspector` | `read`, `survey`, `assistant` | 3D site `/dashboard`, condition `/dashboard/condition`, space watch `/dashboard/watch`, maps `/dashboard/maps`, new map `/dashboard/maps/new`, uploads `/dashboard/uploads`, devices (read only) `/dashboard/devices`, assistant `/dashboard/assistant` |
| مدير الموقع · `site_manager` | `read`, `manage_site`, `manage_devices`, `export`, `assistant` | The shared screens, plus the field photography permit and PDF/CSV downloads on `/dashboard/condition`, camera registry and «التقط الآن» on `/dashboard/devices`, assistant |
| أخصائي الترميم · `expert` | `read`, `survey`, `review`, `export`, `assistant` | Everything an inspector has, plus the review queue `/dashboard/review`, element editing, field inspection and approval on `/dashboard/maps/{id}`, satellite alert acknowledgement, exports |
| ممثل هيئة التراث · `authority` | `read`, `export`, `assistant`, `read_audit` | The shared screens across every site, exports, assistant, and the audit log `/dashboard/audit` with its CSV |
| مهندس النماذج · `ml_engineer` | `read`, `export`, `manage_models` | The shared screens, exports, and the model registry `/dashboard/models` with the training export |
| مسؤول النظام · `admin` | all ten, including `administer` | Everything, plus accounts and roles `/dashboard/users` |

"The shared screens" are the 3D site, condition, space watch and maps pages, which need only `read`. Every signed-in user can change their password at `/dashboard/password`. The full matrix, endpoint list and account lifecycle are in [docs/06-security/roles.md](docs/06-security/roles.md).

## Identity and interface

The web app uses the «حاشية المخطوط» (Manuscript Margin) identity: warm paper ground, iron-gall ink, and a rubric red used for the specialist's voice. Specialist notes and low-confidence warnings sit beside what they describe as a marginal note, never in a popup. Urgent damage has its own darker red and always carries a text label and an icon, so colour is never the only signal.

- Primitives are shadcn/ui components rewritten for the identity in `frontend/src/components/ui/`, with logical properties only and 44 px touch targets.
- Arabic text uses Scheherazade New and Latin text Cormorant Garamond, both self-hosted so the build works offline.
- The app is RTL by default (`<html dir="rtl">` and Radix `Direction.Provider`), uses Arabic-Indic digits, and keeps text contrast at 4.5:1 or more against WCAG 2.2.
- `prefers-reduced-motion` turns animations off.

Tokens, contrast table and component rules: [docs/design/DESIGN.md](docs/design/DESIGN.md).

## Wall damage maps and the glossary

1. An inspector picks a registered facade, or names a free-standing wall with its width and height, takes a photo and drags four handles to the wall corners.
2. The photo goes through the privacy step, then the wall is warped to a front-on view at its real aspect and split into a grid: 8 rows by default (`SADU_MAP_ROWS`), columns follow the wall's shape.
3. The configured detector proposes damage. The map shows each element as an area, a line or a point, measured in metres from the wall size.
4. If the detector fails, the map is still saved empty so the specialist can draw it by hand.
5. The model's original answer is kept, so `GET /maps/accuracy` shows how often the model agrees with the specialist.

The unified glossary in `mapping/domain/glossary.py` has eight core types:

| Type | Arabic | Drawn as | Class |
|---|---|---|---|
| `plaster_loss` | فقدان اللياسة | area | |
| `crack` | التشققات | line | width: under 1 mm, 1 to 5 mm, over 5 mm |
| `basal_erosion` | تآكل القاعدة | area | depth |
| `rain_gully` | أخاديد الأمطار | line | depth |
| `salt_efflorescence` | تزهّر الأملاح | area | |
| `cavity` | الفجوات والجحور | point | size |
| `wall_head` | تلف رؤوس الجدران والشرفات | area | |
| `cement_repair` | ترميمات إسمنتية سابقة | area | |

Four older types (moisture, surface erosion, partial collapse, graffiti) are kept outside the core list for maps drawn before the glossary. Details: [docs/10-damage-maps.md](docs/10-damage-maps.md), [ADR-019](docs/adr/ADR-019-rectified-grid-damage-map.md).

## Workflow and approval

The map page shows the authority's ten steps with their state, output and criterion: photo check, privacy, damage detection, confidence, treatment, materials and tools, unified map, specialist review, approval, approved outputs.

- The specialist changes an element's type, severity or class, confirms it, deletes it, or draws a new one with the mouse or the keyboard (arrow keys and Space). Every change goes into the correction log.
- Approval is refused until a field inspection is recorded and no low-confidence model element is left unreviewed.
- The treatment plan comes from `region-packs/treatments/earthen-najdi.json`: steps, materials scaled to the damaged area, tools, whether a specialist must supervise, and sources. The catalog is a draft that a conservator must review before it is used as advice, and the plan says so ([ADR-020](docs/adr/ADR-020-treatment-catalog.md)).
- "حمّل التقرير PDF" downloads an Arabic A4 report of the wall; `elements.csv` gives the elements table. A draft map is marked as a draft on the page ([ADR-024](docs/adr/ADR-024-wall-report-pdf.md)).
- The site manager reads the site condition summary on `/dashboard/condition`, downloads it as PDF or CSV, and grants or withdraws the field photography permit. Visitor photo missions run only on sites with a permit.

Details: [ADR-026](docs/adr/ADR-026-diriyah-agent-workflow.md).

## Satellite watch and early warning

1. Weekly (`SADU_WATCH_INTERVAL_H`, default 168) and on demand, the API pulls Sentinel-2 scenes for each site from Element 84 Earth Search and builds two median composites: the last 30 days and the year before.
2. Pixels that moved more than three times their usual spread, in clusters of at least three, are labelled water, vegetation loss, construction, sand or earthworks, inside the site or in the 150 m ring around it.
3. A risk score ranks the sites. `/dashboard/watch` shows the ranking on a map and, per site, a before/after slider and a change map.
4. The early warning compares each scan with one at least five days older: the trend is new, rising, steady or falling, and a threat seen in both scans is confirmed. An urgent scan, or a moderate one with a confirmed threat, sends an alert to `SADU_ALERT_WEBHOOK_URL`.
5. **Ground check** opens high-priority photo missions on the site's facades. A site without registered facades tells the inspector a visit is needed.

10 m pixels catch changes around a site, not cracks: the satellite layer screens, and wall maps confirm. `SADU_SCENE_SOURCE=sample` serves labelled synthetic scenes with invented events from `region-packs/riyadh/sample-events.json`, and every scan from it is marked as sample data. Details and limits: [ADR-025](docs/adr/ADR-025-space-watch.md), [region-packs/riyadh/README.md](region-packs/riyadh/README.md).

## Cameras, drones and bulk upload

- **Cameras.** Register fixed cameras on `/dashboard/devices` with the snapshot URL most IP cameras and NVRs expose. The API captures each one every `SADU_CAMERA_INTERVAL_H` hours (default 24) or on «التقط الآن», and keeps every attempt in the camera's history.
- **Uploads.** Staff with `survey` upload 1 to 30 photos of up to 8 MB on `/dashboard/uploads`, from a phone, a drone survey or an archive. They pick the wall, or Athar matches it from the photo's GPS: the nearest facade facing the photo position, within 60 m of a site. Photos without GPS wait for someone to pick the facade.
- **Jobs.** Each photo becomes a job. The worker reads GPS and capture time, blurs faces and strips EXIF, then creates a draft map through the same detector, workflow and approval as a hand-drawn one. The map shows its source: inspector, camera name, drone or upload.
- **Safety.** Camera addresses inside private networks are refused unless listed in `SADU_CAMERA_ALLOWED_HOSTS`, and cloud metadata addresses stay blocked. Camera passwords live only in `SADU_CAMERA_SECRET_*` environment variables; the database holds the variable name.

In demo mode, seeding the demo pack adds a camera on the demo building's north facade that reads a test photo served by the API, so the camera flow works offline. Details: [ADR-027](docs/adr/ADR-027-ingestion.md).

## The assistant

`/dashboard/assistant` is a chat for staff with the `assistant` permission. They attach wall photos, drone photos or PDFs of old inspection reports and ask in Arabic. The assistant picks one of five inspection skills (Markdown files in `backend/src/sadu/modules/assistant/skills/`): wall photo inspection, drone roof and wall head, satellite alert review, treatment check, and audit report. It follows the skill's steps with tools from the other modules and streams each step.

- A photo of a named facade becomes a draft wall map, only for users with `survey`. The assistant cannot approve maps, edit elements or approve treatments.
- «صياغة ملف التدقيق» renders an Arabic PDF with the photos, the elements table, catalog treatments, recommendations and a «يتطلب اعتماد المختص» stamp.
- Sending the file to specialists waits for «أكّد الإرسال». The confirmed send goes to `SADU_SPECIALIST_WEBHOOK_URL` and is written to the audit log.
- When the model is down or the daily budget is spent, the chat says so and «حلّل الصورة» still analyses photos directly. In demo mode without a model key, a scripted planner runs the same flow offline.

Details, privacy and failure modes: [ADR-028](docs/adr/ADR-028-assistant.md).

## Athar's own model

Approved maps train a damage model the authority owns, so it does not depend on a paid API. It is Qwen3.5-4B (Apache-2.0, natively multimodal) fine-tuned with bf16 LoRA. It reads the rectified photo and answers with glossary elements: type, shape, severity, class and confidence.

1. A model engineer downloads approved maps from `GET /api/v1/ml/training-export` (`manage_models`). Faces were blurred at upload, and no user or visitor data is exported.
2. `ml/data/collect.py` fetches nine licence-checked public sets on its own (heritage walls in Cairo, the Kasbah of Algiers and Darbhanga Fort, brick masonry, concrete crack sets and crack masks) from Zenodo, Mendeley Data and the Hugging Face Hub; `ml/data/build_dataset.py` splits Athar maps by site and holds out 10% of the public close-ups, so test scores come from walls and photos the model never saw.
3. `ml/notebooks/train_qwen35_damage.ipynb` runs on Google Colab. It reads the GPU and picks the profile: Qwen3.5-4B in bf16 LoRA on a 22 GB L4, 9B on an A100, 2B below 16 GB. It scores the base model first, then the fine-tuned model on the same held-out rows, evaluates wall maps with the same cell matching as the accuracy card, and exports GGUF files.
4. Inference runs on a 16 GB machine with llama.cpp `llama-server` and the Q4_K_M GGUF plus its vision projector, about 5 GB in use.
5. The version is registered with its metrics and activated on `/dashboard/models`. With `SADU_DAMAGE_DETECTOR=qwen`, new maps use the active version and the audit log records it.

The model has not been trained yet. It can be trained now on the public close-ups, which gives a before/after number on held-out heritage photos; the wall-map score waits for approved maps. Details: [ADR-029](docs/adr/ADR-029-own-model.md), [docs/ml/architecture.md](docs/ml/architecture.md), [ml/README.md](ml/README.md).

## Governance

- **Roles.** Six roles over ten permissions, denied by default (see [Features by role](#features-by-role)).
- **Site scope.** An admin can limit an account to chosen sites. A resource outside the scope answers 404, the same as one that does not exist. `admin` and `authority` always see every site.
- **Accounts.** Temporary passwords of at least 12 characters, a forced change on first sign-in, deactivation that ends every session, and no way for an admin to demote or deactivate themselves.
- **Audit log.** Sign-ins, account changes, every step of a map from creation to approval, finding reviews, permits, missions, satellite actions, passport deletions, retention runs and notices. `authority` reads it on `/dashboard/audit`; the CSV also needs `export`. No endpoint edits or deletes audit rows.
- **Exports.** CSV files start with a UTF-8 byte order mark for Excel and neutralise cells that start with `=`, `+`, `-` or `@`.
- **Notices.** An urgent-damage notice the first time a map holds urgent elements, and a reminder for each draft waiting longer than `SADU_APPROVAL_OVERDUE_DAYS` (default 7). Both go to `SADU_ALERT_WEBHOOK_URL` and are recorded in the audit log first, so none is sent twice.

Details: [docs/06-security/roles.md](docs/06-security/roles.md).

## Privacy and PDPL

- Faces are blurred (YuNet) and EXIF removed before any photo is stored or sent to a model, from every source ([ADR-015](docs/adr/ADR-015-privacy-processing.md)).
- Visitors share location and heading only after consent; without it, they are dropped. Location is discarded once the facade is known.
- Visitor photos are kept 30 days, or two years when they are evidence for a published finding. A background loop purges expired photos, and a visitor can delete their passport and every non-evidence photo from the passport page.
- Drone and staff photos lose GPS and faces before storage; the job keeps the GPS reading and capture time so a reviewer can see where the photo was taken.
- With `SADU_DAMAGE_DETECTOR=qwen` and `llama-server` on the authority's own machine, wall photos are analysed on-premises and do not leave the country. Two exceptions remain: training on Colab sends blurred, rectified wall photos to Google's cloud, and the visitor agents still send blurred photo regions to the hosted model (the assistant sends it only text and tool results).

Threat model: [docs/06-security/threat-model.md](docs/06-security/threat-model.md).

## Visitors

The visitor app opens from a QR code without installing anything. A visitor photographs a facade, hears a sourced story of the place in Arabic, and collects a passport stamp. Agents compare the photo with the facade's baseline, and a change is published only with evidence; uncertain or urgent findings wait in the specialist's review queue. Visitors also get a 3D view of the site on Google Maps and directions to it. Details: [docs/03-architecture.md](docs/03-architecture.md), [ADR-005](docs/adr/ADR-005-damage-pipeline.md), [ADR-022](docs/adr/ADR-022-google-maps-3d-site-view.md).

## Architecture

A modular monolith: one FastAPI deployable split into sixteen modules under `backend/src/sadu/modules/`. Each module exposes one `api.py` that the others may import; inside it, layers point inward (`interface → api → infrastructure → application → domain`). import-linter fails the build on any other import ([ADR-001](docs/adr/ADR-001-modular-monolith.md)).

| Module | Owns |
|---|---|
| `admin` | Users, sessions, roles and permissions, site scope, audit log, model cost counter |
| `agents` | The LangGraph run for each visitor photo, finding reviews, the retention purge |
| `assistant` | Staff chat: inspection skills, tool calls into other modules, audit files, confirmed sends |
| `capture` | Upload processing: EXIF strip, face blur, resize, idempotency |
| `ingest` | Devices, ingest jobs, camera capture, the job worker, GPS facade matching |
| `inspection` | Photo quality gate, alignment to the baseline, difference map, model judgment |
| `mapping` | Wall maps, rectification, grid, glossary elements, detector port, corrections, workflow, approval, accuracy |
| `missions` | Photo missions for coverage gaps and ground checks |
| `models` | Own-model registry and the training export |
| `passport` | Anonymous visitor passports and stamps |
| `reports` | Wall report PDF, elements CSV, site condition summary, PDF and CSV, assistant audit PDF |
| `sites` | Region packs, sites, facades, baselines, field photography permit |
| `stories` | Story sources, retrieval and drafted claims for visitors, cached stories |
| `treatments` | Treatment catalog and plans scaled by damaged area |
| `verification` | Evidence rule, findings, review queue, pins |
| `watch` | Sentinel-2 screening, risk score, early warning, alert webhook |

```mermaid
flowchart LR
  browser["Browsers<br/>visitor phones, staff laptops"] --> caddy
  subgraph host["One VM, Docker Compose"]
    caddy["Caddy<br/>TLS in the prod profile"]
    web["web<br/>Next.js"]
    api["api<br/>FastAPI and background loops"]
    db[("db<br/>Postgres 18, PostGIS, pgvector")]
    storage[("storage<br/>SeaweedFS S3")]
  end
  subgraph outside["Outside services"]
    claude["Anthropic API"]
    qwen["llama-server<br/>own model, optional"]
    stac["Earth Search<br/>Sentinel-2"]
    speech["Azure Speech, optional"]
    cameras["Site cameras"]
    hooks["Webhooks<br/>alerts, specialists"]
  end
  caddy --> web
  caddy -->|/api| api
  api --> db
  api --> storage
  api --> outside
```

### Stack

| Layer | Technology and version |
|---|---|
| API | Python 3.13, FastAPI 0.163.1, Pydantic 2.14.3, Uvicorn 0.54.0, sse-starlette 3.7.0 |
| Data | PostgreSQL 18 with PostGIS 3.7 and pgvector 0.8.7, SQLAlchemy 2.1.8, GeoAlchemy2 0.21.0, Alembic 1.20.1, psycopg 3.3.9 |
| Agents and models | LangGraph 1.2.22 with the Postgres checkpointer 3.2.1, Anthropic SDK 2.9.0, httpx 0.28.1 for HTTP and own-model detectors |
| Vision and imagery | OpenCV 5.0, scikit-image 0.26.0, Pillow 13.0.0, NumPy 2.5.5, rasterio 1.5.2 or later, SciPy 1.16 or later |
| Files and reports | S3 API with boto3 1.44.3 (SeaweedFS 4.54 locally), WeasyPrint 70 or later, Jinja2 3.1.6 or later |
| Ops | structlog 26.1.0, Sentry SDK 2.75.0, Argon2 (argon2-cffi 25.1.0), Caddy 2.11.9 |
| Web | Node 24, Next.js 16.4.6, React 19.3.0, TypeScript 5, Tailwind CSS 4.3.3, Radix UI 1.8.1 with shadcn/ui, lucide-react 1.75.0, sonner 2.0.8 |
| 3D and maps | three.js 0.187.0, React Three Fiber 9.8.2, drei 10.7.9, `@vis.gl/react-google-maps` 1.10.2 |
| Quality | pytest 9.2.0, ruff 0.17.5, mypy 2.4.1 strict, import-linter 2.16, pip-audit 2.10.1, ESLint 9, Vitest 5.1.1, Playwright 1.65.1 |
| Own model (Colab) | transformers 5.17.0, Unsloth 2026.11.6, TRL 1.15.0, PEFT 0.21.3; llama.cpp for serving |

Versions come from `backend/pyproject.toml`, `frontend/package.json` and `ml/requirements-colab.txt`. Reasons and alternatives: [docs/04-stack.md](docs/04-stack.md) and the [ADRs](docs/adr/).

## Running it

### Quick start with Docker

You need Docker with Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

The `migrate` service applies migrations and the `seed` service loads two region packs. `region-packs/demo` is a synthetic test building with four facades, not a heritage site. `region-packs/riyadh` holds eleven heritage sites in the Riyadh region, including At-Turaif and Al-Faw, with approximate boundaries and no facades yet ([details](region-packs/riyadh/README.md)).

Create a dashboard account. The role is one of `inspector`, `site_manager`, `expert`, `authority`, `ml_engineer` or `admin` (default `inspector`):

```bash
docker compose run --rm -e SADU_NEW_USER_PASSWORD='choose-12-chars-or-more' api \
  python -m sadu.cli create-user admin@example.com --role admin
```

Sign in as that admin to create the other accounts on `/dashboard/users`. Test photos are in `region-packs/demo/test-photos/`.

| What | URL |
|---|---|
| Visitor app | http://localhost:3000 |
| Dashboard | http://localhost:3000/dashboard |
| Wall damage maps | http://localhost:3000/dashboard/maps |
| Space watch | http://localhost:3000/dashboard/watch |
| Bulk upload | http://localhost:3000/dashboard/uploads |
| Cameras and devices | http://localhost:3000/dashboard/devices |
| Assistant | http://localhost:3000/dashboard/assistant |
| API docs (not served when `SADU_ENV=prod`) | http://localhost:8000/api/docs |
| Health check | http://localhost:8000/api/v1/healthz |
| Object store | http://localhost:8333 |

For a public demo on a VM, set `SADU_DOMAIN`, `SADU_ENV=prod`, real secrets and `ANTHROPIC_API_KEY` in `.env`, then run `docker compose --profile prod up -d`. Caddy gets TLS certificates and serves the app on 443.

### Demo mode

For a demo without a network, set these in `.env` before `docker compose up`:

```bash
SADU_DEMO_MODE=true
SADU_SCENE_SOURCE=sample
```

- Model answers recorded during earlier live runs are replayed first (`demo-cache` volume). Without a recording or a key, a wall map opens empty for the specialist to draw.
- The demo seed adds a camera that reads a test photo from the API itself.
- The assistant uses a scripted planner when there is no model key.
- The satellite page shows synthetic scenes, labelled as sample data.

### Local development

Start the database and object store, then run the API from `backend/` (it reads `backend/.env`; the defaults match the compose services):

```bash
docker compose up -d db storage
cd backend
uv sync
mkdir -p models && curl -fsSL -o models/face_detection_yunet_2023mar.onnx \
  https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
uv run alembic upgrade head
uv run python -m sadu.cli seed --pack demo
uv run python -m sadu.cli seed --pack riyadh
SADU_NEW_USER_PASSWORD='choose-12-chars-or-more' uv run python -m sadu.cli create-user you@example.com --role admin
uv run uvicorn sadu.main:app --reload --port 8000
```

Then the web app from `frontend/`:

```bash
npm ci
SADU_API_ORIGIN=http://localhost:8000 npm run dev
```

More in [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

## Environment variables

Every variable is optional in development. In production (`SADU_ENV=prod`) the API refuses to start without `ANTHROPIC_API_KEY` and `S3_SECRET_ACCESS_KEY`, or with the dev database password.

| Variable | Default | What it does |
|---|---|---|
| `SADU_ENV` | `dev` | `dev`, `test` or `prod`; `prod` enforces the secrets above and hides the API docs |
| `SADU_PUBLIC_ORIGIN` | `http://localhost:3000` | Origin of the web app, used for CORS and in links sent by notices |
| `DATABASE_URL` | `postgresql+psycopg://sadu:dev@localhost:5432/sadu` | Database; compose builds it from `POSTGRES_PASSWORD` |
| `POSTGRES_PASSWORD` | `dev` | Compose only: password of the `db` service; change it for anything public |
| `S3_ENDPOINT_URL` | `http://localhost:8333` | Object store the API talks to (`http://storage:8333` in compose) |
| `S3_PUBLIC_ENDPOINT_URL` | none | Object store address used in presigned URLs for the browser |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | `devkey`, `devsecret123` | Object store credentials; the secret is required in prod |
| `S3_BUCKET`, `S3_REGION` | `sadu`, `us-east-1` | Bucket and region |
| `ANTHROPIC_API_KEY` | none | Hosted model for the grid detector, visitor agents, stories and the assistant; required in prod |
| `SADU_MODEL_MAIN`, `SADU_MODEL_FAST` | `claude-sonnet-5-5`, `claude-haiku-5-5` | Hosted model names for judgment and for routing |
| `SADU_DAILY_LLM_BUDGET_USD` | `10` | Daily spend cap; calls past it fail over to the fallbacks |
| `SADU_DEMO_MODE` | `false` | Replay recorded model answers first, seed the demo camera, scripted assistant without a key |
| `SADU_DEMO_CACHE_DIR` | `demo-cache` | Where recorded model answers are kept |
| `SADU_MAX_CONCURRENT_RUNS` | `4` | Visitor photo runs processed at once |
| `SADU_YUNET_MODEL_PATH` | `models/face_detection_yunet_2023mar.onnx` | Face detection model for the blur |
| `SADU_REGION_PACKS_DIR` | `../region-packs` (`/region-packs` in Docker) | Region packs, sample events and the treatment catalog |
| `SADU_DAMAGE_DETECTOR` | `claude` | `claude`, `http_detection`, `http_cell_classification`, `qwen` or `none` |
| `SADU_DETECTOR_URL`, `SADU_DETECTOR_TOKEN` | none | Endpoint and token of a ready model; required for the two `http_*` detectors |
| `SADU_DETECTOR_LABELS` | empty | JSON map from model labels to damage types, e.g. `{"spalling": "plaster_loss"}` |
| `SADU_DETECTOR_MIN_SCORE` | `0.35` | Drop weaker predictions |
| `SADU_DETECTOR_TIMEOUT_S` | `30` | Seconds per call to a ready model |
| `SADU_QWEN_URL` | `http://localhost:8080/v1` | OpenAI-compatible server of the own model |
| `SADU_QWEN_MODEL` | `athar-damage` | Model name used until a version is activated |
| `SADU_QWEN_TOKEN` | none | Bearer token, only if the server checks one |
| `SADU_QWEN_TIMEOUT_S` | `120` | Seconds per photo |
| `SADU_QWEN_JSON_SCHEMA` | `true` | Send the answer schema as `response_format` |
| `SADU_MAP_ROWS` | `8` | Grid rows per wall map, 2 to 20 |
| `SADU_TREATMENT_CATALOG` | `region-packs/treatments/earthen-najdi.json` | Treatment catalog file |
| `SADU_SCENE_SOURCE` | `earth_search` | `earth_search` (Sentinel-2 on AWS), `sample` (synthetic) or `none` |
| `SADU_SCENE_SEARCH_URL` | Element 84 Earth Search v1 | STAC search endpoint |
| `SADU_WATCH_INTERVAL_H` | `168` | Hours between automatic scans per site; `0` turns the schedule off |
| `SADU_WATCH_SAMPLE_EVENTS` | `region-packs/riyadh/sample-events.json` | Events used by the sample scene source |
| `SADU_ALERT_WEBHOOK_URL` | empty | HTTPS webhook for satellite alerts and governance notices; without it they stay on the dashboard and in the audit log |
| `SADU_SPECIALIST_WEBHOOK_URL` | empty | HTTPS webhook for audit files confirmed in the assistant; without it the send is audited but not delivered |
| `SADU_RETENTION_INTERVAL_H` | `24` | Hours between purges of expired visitor photos; `0` turns it off |
| `SADU_APPROVAL_OVERDUE_DAYS` | `7` | Days before a draft map gets an approval reminder; `0` turns it off |
| `SADU_CAMERA_INTERVAL_H` | `24` | Hours between captures for cameras without their own interval; `0` turns scheduled capture off |
| `SADU_CAMERA_ALLOWED_HOSTS` | empty | Host names and CIDR ranges of cameras on private networks, e.g. `nvr.site.local,10.20.0.0/16` |
| `SADU_CAMERA_SECRET_<NAME>` | none | One per camera password; the device stores only the variable name |
| `SADU_INGEST_CONCURRENCY` | `2` | Ingest jobs analysed at once, 1 to 8 |
| `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | none | Arabic audio for visitor stories; without them the story is text only |
| `SADU_TTS_VOICE` | `ar-SA-HamedNeural` | Speech voice |
| `SENTRY_DSN_API` | none | Error reports from the API |
| `GOOGLE_MAPS_API_KEY` | none | Web app: 3D site view and in-app routes; restrict it to your domain |
| `SADU_API_ORIGIN` | `http://localhost:8000` | Web app in development: where `/api` is proxied |
| `SADU_DOMAIN` | `localhost` | Domain for Caddy in the `prod` profile |
| `SADU_NEW_USER_PASSWORD` | prompt | CLI only: password for `create-user` |

`docker-compose.yml` passes most API variables to the `api` service. It does not pass the `SADU_QWEN_*`, `SADU_CAMERA_SECRET_*`, `SADU_MODEL_*` or `SADU_DETECTOR_TIMEOUT_S` variables; add those to the `api` service in a `compose.override.yaml`. Inside the container, `localhost` is the container itself, so point `SADU_QWEN_URL` at the host (for example `http://host.docker.internal:8080/v1`) when `llama-server` runs on the host.

## Testing and quality

Backend, from `backend/`, with Postgres from compose and a test database. Tests default to `sadu_test`, and the integration tests that commit are skipped on any database whose name does not end in `_test`:

```bash
docker compose exec db createdb -U sadu sadu_test
export DATABASE_URL=postgresql+psycopg://sadu:dev@localhost:5432/sadu_test
uv run alembic upgrade head
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports
uv run python -m eval.run
uv run python -m sadu.cli quality
uv run pytest ../ml/tests
```

Frontend, from `frontend/`:

```bash
npm ci
npm run lint && npm run typecheck && npm test && npm run build
npx playwright install chromium
E2E_EXPERT_EMAIL=you@example.com E2E_EXPERT_PASSWORD='…' npm run e2e
```

The end-to-end tests need the stack running, seeded, and an expert account.

Evaluation tools:

- `uv run python -m eval.score_maps <folder> --min-accuracy 0.8` scores a detector on labelled wall photos ([format](docs/10-damage-maps.md#measuring-accuracy-before-the-demo)).
- `uv run python -m eval.backtest_watch run …` then `score …` replays satellite screening over past dates and measures its precision against a hand-filled truth column.
- `uv run python -m sadu.cli quality` reads the live database and prints the share of published findings and approved maps that carry full evidence, photos sent back, findings held for a specialist, specialist rejections and corrected maps. It exits non-zero when anything reached the dashboard without evidence. The same report is `GET /api/v1/reports/quality` (`read_audit`) and the card on the audit page.

Counted on 2026-11-18 on this branch: 403 backend tests, 48 frontend unit tests in 10 files, and 45 ML script tests (one more runs where pyarrow is installed), all passing.

What CI runs ([.github/workflows/ci.yml](.github/workflows/ci.yml)) on every push to `main` and every pull request:

| Job | Steps |
|---|---|
| backend | ruff check and format, mypy strict, import-linter, migrations with `alembic check`, pytest, the vision evaluation on the demo pack, pip-audit |
| frontend | ESLint, `tsc --noEmit`, Vitest, `next build`, `npm audit` |
| e2e | The stack in Docker with `SADU_DAMAGE_DETECTOR=none` and sample scenes, seed, an expert account, Playwright |
| security | gitleaks, Semgrep, Trivy filesystem and IaC scan |
| docs | Renders every Mermaid diagram under `docs/` |

CI does not run the ML script tests or render the Mermaid in this README. The **Space watch live check** workflow runs the satellite backtest against live Sentinel-2 by hand and uploads the table and evidence images.

## Documentation

| Topic | File |
|---|---|
| Scope and requirements | [docs/00-scope.md](docs/00-scope.md) |
| Research and market comparison | [docs/01-research.md](docs/01-research.md) |
| Team roles | [docs/02-roles.md](docs/02-roles.md) |
| Architecture, API contract, data | [docs/03-architecture.md](docs/03-architecture.md) |
| Stack and versions | [docs/04-stack.md](docs/04-stack.md) |
| Phases | [docs/05-phases.md](docs/05-phases.md) |
| Security and threat model | [docs/06-security/threat-model.md](docs/06-security/threat-model.md) |
| Roles, permissions and governance | [docs/06-security/roles.md](docs/06-security/roles.md) |
| Infrastructure, monitoring, testing | [docs/07-infra-and-testing.md](docs/07-infra-and-testing.md) |
| Verification and demo script | [docs/09-verification-and-demo.md](docs/09-verification-and-demo.md) |
| Wall damage maps | [docs/10-damage-maps.md](docs/10-damage-maps.md) |
| UML: use cases, components, classes, sequences, states, ER, deployment | [docs/11-uml.md](docs/11-uml.md) |
| Design contract | [docs/design/DESIGN.md](docs/design/DESIGN.md) |
| Own damage model | [docs/ml/architecture.md](docs/ml/architecture.md), [ml/README.md](ml/README.md) |
| Riyadh region pack | [region-packs/riyadh/README.md](region-packs/riyadh/README.md) |

### Decisions (ADR-001 to ADR-029)

| ADR | Decision |
|---|---|
| [001](docs/adr/ADR-001-modular-monolith.md) | Modular monolith with hexagonal module boundaries |
| [002](docs/adr/ADR-002-langgraph-orchestration.md) | LangGraph orchestrator-worker graph with Postgres checkpointer and interrupts |
| [003](docs/adr/ADR-003-llm-claude.md) | Claude Sonnet 5.5 and Haiku 5.5 behind an LLM port |
| [004](docs/adr/ADR-004-postgres-postgis-pgvector.md) | One PostgreSQL 18 database with PostGIS and pgvector |
| [005](docs/adr/ADR-005-damage-pipeline.md) | Classical alignment, difference map and model judgment with a deterministic label rule |
| [006](docs/adr/ADR-006-object-storage.md) | S3 API behind a port; SeaweedFS locally instead of MinIO |
| [007](docs/adr/ADR-007-3d-twin.md) | GLB mesh with facade planes; Gaussian splat optional |
| [008](docs/adr/ADR-008-background-jobs.md) | In-process background tasks and SSE, no queue in Round 1 |
| [009](docs/adr/ADR-009-embeddings.md) | BGE-M3 embeddings locally behind a port, with full-text fallback |
| [010](docs/adr/ADR-010-tts.md) | Azure AI Speech with a Saudi Arabic neural voice, cached |
| [011](docs/adr/ADR-011-auth.md) | Local dashboard accounts with server sessions; anonymous passport tokens for visitors |
| [012](docs/adr/ADR-012-frontend.md) | One Next.js app with visitor and dashboard route groups |
| [013](docs/adr/ADR-013-demo-hosting.md) | One VM running Docker Compose behind Caddy |
| [014](docs/adr/ADR-014-observability.md) | Langfuse for model traces, Sentry for errors, structlog for logs |
| [015](docs/adr/ADR-015-privacy-processing.md) | Process before store: EXIF strip and face blur before storage or any model call |
| [016](docs/adr/ADR-016-build-time-changes.md) | Changes made while building Round 1 |
| [017](docs/adr/ADR-017-diriyah-challenge-alignment.md) | Aim Round 1 at the Diriyah wall damage challenge |
| [018](docs/adr/ADR-018-damage-detector-port.md) | Damage detection behind a port: hosted model or a ready model |
| [019](docs/adr/ADR-019-rectified-grid-damage-map.md) | Damage map as a grid on the rectified wall |
| [020](docs/adr/ADR-020-treatment-catalog.md) | Treatments come from a reviewed catalog, not from the model |
| [021](docs/adr/ADR-021-frontend-page-folders.md) | Each page keeps its own components |
| [022](docs/adr/ADR-022-google-maps-3d-site-view.md) | Show the site in 3D on Google Maps, with directions |
| [023](docs/adr/ADR-023-sites-without-facades.md) | A site can exist before its facades |
| [024](docs/adr/ADR-024-wall-report-pdf.md) | Wall reports are PDFs rendered on the server |
| [025](docs/adr/ADR-025-space-watch.md) | Screen site surroundings from Sentinel-2 and send alerts to the ground |
| [026](docs/adr/ADR-026-diriyah-agent-workflow.md) | The Diriyah ten-step workflow, the unified glossary and role permissions |
| [027](docs/adr/ADR-027-ingestion.md) | Bring photos in from site cameras, drones and bulk uploads |
| [028](docs/adr/ADR-028-assistant.md) | «مساعد أثر», a staff chat that inspects files with skills and drafts audit files |
| [029](docs/adr/ADR-029-own-model.md) | Athar's own damage model on Qwen3.5 |

## Limitations

- **Accuracy on real walls is not measured yet.** No detector has been scored against specialists on real Najdi walls, and the treatment catalog has not been reviewed by a conservator ([docs/10-damage-maps.md](docs/10-damage-maps.md)). The tools to measure it (`eval.score_maps`, the accuracy card) are ready.
- **Sample satellite data in the demo.** An offline demo uses synthetic scenes with invented events. They are labelled as sample data and say nothing about the real sites.
- **The own model is not trained.** The pipeline waits for approved maps; until then the hosted grid detector or manual drawing produce the maps.
- **PDFs in the assistant are stored, not read.** They are listed as references in the audit file; the user summarises what matters in the chat.
- **RTSP needs ffmpeg.** The API image does not include it, so only cameras with an HTTP snapshot URL work in the Docker deployment.
- **One API process.** The schedulers (satellite scans, camera captures, the ingest worker, missions, retention, overdue reminders) run inside the API process. A second process would duplicate scheduled captures until a lease is added.
- **The hosted model is still required in production.** Even with the own model as the wall detector, visitor agents, stories and the assistant use the hosted model, and `SADU_ENV=prod` requires its key.
- **Visitor findings are not site-scoped.** Finding detail, pins and the visitor review queue are visible to every staff account with the right permission ([roles.md §5](docs/06-security/roles.md#5-نطاق-المواقع--site-scope)).
