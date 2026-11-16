# 05 · Phases

Times are Riyadh time (UTC+3). The bootcamp session schedule is not known yet (TBD); blocks below shift around sessions but keep their order. Each block is 2 hours.

## Phase 0 · Preparation (Nov 16-17, before Nov 18)

| Area | Task | Owner | Done when |
|---|---|---|---|
| Building | Choose the building, get permission (or written owner OK) | UX | Name and permission status written in `region-packs/<pack>/site.md` |
| Scan | Capture photogrammetry (and optionally a splat) in one visit | UX + DS | Raw capture files backed up in two places |
| Baselines | Primary frontal baseline per facade (4-6) + 3-5 extra angles per facade | DS | Files named `<facade_code>_baseline.jpg`, EXIF kept only in the private raw folder |
| Test set | 50 photos: 25 no-change, 25 with change (existing damage vs older baseline, or reversible staged change: tape, chalk, removable printed sheets) | DS | `data/testset/labels.csv` with columns `file, facade_code, has_change, damage_type, region_bbox, notes` |
| 3D | Blender cleanup, facade corners, GLB export, compression | UX + DS | GLB <= 15 MB opens in the gltf viewer; `facade_map.json` validates against the schema |
| Sources | Collect official sources about the building and any reviewed oral account (with narrator consent) | UX | `sources/` with title, URL or narrator, license; nothing written from memory |
| Repo | Create repo (name TBD), branch protection, CI skeleton, issue board | Dev | CI runs lint on an empty project |
| Environments | API keys (Anthropic, Azure Speech, Sentry) in a shared secret store; VM created; DNS name | Dev | `.env` exists on the VM only; `.env.example` committed |
| Contracts | facade_map, Finding, SSE events, Story schemas frozen (from 03-architecture) | Tech lead | Merged in `docs/` and as Pydantic/TS types |

## Phase 1 · Round 1 build (Nov 18-20)

| Time | AI engineer | Data scientist | Developer | UX/Product | Done when |
|---|---|---|---|---|---|
| **Nov 18** 09-11 | LLM port + Anthropic adapter with structured output, timeouts, cost logging | Load baselines; quality gate functions + unit tests | Scaffold API (modules, shared/, health), compose with db + storage, Alembic base | Visitor flow wireframes (capture, overlay, story, passport) | `docker compose up` serves `/healthz`; one structured LLM call returns valid JSON in a test |
| 11-13 | Graph skeleton: plan → identify → monitor → verify → guide with stub nodes, Postgres checkpointer | SIFT + MAGSAC alignment on baseline/test pairs; record inlier stats | Sites module + region pack import (facades, baselines, GLB key) | Dashboard wireframes (3D + pins + evidence panel, review queue) | Pack import loads the demo building; graph runs end to end with stubs |
| 14-16 | Identifier node (GPS, heading, image match, ask-visitor interrupt) | Normalization + difference map + lighting flag; heat-map PNG | Capture: upload endpoint, validation, EXIF strip, face blur, idempotency, storage | Arabic copy + RTL design tokens | Upload of a test photo creates an observation and a blurred stored image |
| 16-18 | Monitor judge prompt + `DamageJudgment` schema; run on 10 test pairs | Tune difference thresholds on 10 pairs | SSE status endpoint + observation status updates | Story screen design; collect remaining sources | Monitor returns regions + judgment for 10 pairs; SSE shows each step |
| 19-21 | Verification domain: label rule + severity floor + unit tests | Eval harness v0 (detection precision/recall on available labels) | Frontend scaffold (Next.js, Tailwind RTL, route groups), capture page with camera, GPS, heading | Pitch outline with the Sadu weaving story | Label rule tests pass; phone can capture and upload on the LAN |
| **Nov 19** 09-11 | Verifier node wiring, evidence linking, expert-review interrupt | Facade corner clicks on baselines → `h_img_to_uv`; pin math tests | Findings, pins and evidence API; presigned URLs | Usability check of capture flow with 2 people | A test photo produces a published pin with evidence in the DB |
| 11-13 | Stories: chunking + BGE-M3 embeddings + retrieval | Run full test set through pipeline, error analysis | Dashboard 3D viewer: GLB + facade planes + pins | Overlay UX polish (opacity, framing hints) | Pins visible on the 3D model at the right facade |
| 14-16 | Guide: draft story with claim citations + claim checking | Threshold tuning round 2 | Evidence panel + review queue UI | Story copy review (MSA, no invented facts) | Story with labeled claims and sources shows on the phone |
| 16-18 | TTS adapter + audio cache; passport entries | Facade identification accuracy metric in harness | Passport page; retake and question screens | Prepare demo photos (scripted set) | Audio plays; visitor can answer a facade question and the run resumes |
| 19-21 | Orchestrator planning with Haiku + fallback; mission dispatch job | Hallucination test set (20 story questions) | Coverage view + missions API + nearby missions in PWA | Demo script draft v1 | Mission appears on the phone near the site (simulated location) |
| **Nov 20** 09-11 | Demo mode cache (by content hash); failure drills (LLM down) | Eval run 1: all metrics printed | Deploy to VM behind Caddy; HTTPS camera test on phones | Recorded backup take 1 | Full flow works on the public URL |
| 11-13 | `llm_calls` cost counter checks | Fix the top 3 error causes from eval | Security headers, CSP, CORS, rate limits; CI scans green | Pitch deck v1 | CI green incl. security scans; eval prints all metrics |
| 14-16 | Prompt fixes from eval; freeze prompts | Eval run 2; write results table | E2E Playwright happy path; bug fixes | Demo rehearsal 1 (timed) | E2E passes in CI; rehearsal under 3 minutes |
| 16-18 | Bug fixes from rehearsal | Prepare evaluation slide (numbers + false-positive rate, honest) | Bug fixes; backups configured | Recorded backup take 2 (final) | Two clean runs without manual fixes |
| 19-21 | Code freeze, tag `round1` | README evaluation section | README run instructions | Submission text | Tag pushed; all Nov 21 checklist items ticked or listed as known gaps |

**Cut list** (in this order if behind schedule): mission ranking by LLM (keep deterministic), Haiku facade tie-break, TTS (text only), passport page polish, expert review UI (keep API + simple list).

## Nov 21 · Delivery checklist

- [ ] Public HTTPS demo URL works on two different phones and one laptop.
- [ ] Recorded 3-minute demo video uploaded (and stored offline).
- [ ] Repository tagged `round1`; README explains run, env vars, tests, evaluation.
- [ ] Evaluation output (all success metrics) committed as `eval/results/round1.md`.
- [ ] Pitch deck with the Sadu weaving story, problem, demo, metrics, business assumptions marked as assumptions.
- [ ] Known gaps and TBDs listed honestly.
- [ ] Demo accounts (inspector, expert) created; passwords shared only with the team.
- [ ] API keys have spending limits set.

## Phase 2 · Round 2 (Nov 28-30, Riyadh)

| Area | Addition | Owner |
|---|---|---|
| Dashboard | Heat map of facades by severity-weighted findings | Dev + UX |
| Dashboard | Timeline slider on one spot using sample data (clearly labeled as sample) | Dev + DS |
| Reports | Restoration report PDF (WeasyPrint, RTL) | AI + Dev |
| National map | MapLibre map with UNESCO region packs (catalog data only, verified from whc.unesco.org; no invented details) | UX + Dev |
| Evaluation | Larger test set, per-damage-type metrics, Verifier on/off hallucination comparison | DS + AI |
| Business | Interview notes from mentors, pricing assumption per site per year (TBD), pilot proposal | UX |
| Polish | Offline queueing in PWA if time remains | Dev |

## Phase 3 · After the hackathon: path to a pilot

1. **Partner and permissions**: one authority, one district, 5-10 buildings; written permission for scans and visitor signage; data processing agreement under PDPL including the LLM provider question.
2. **Security hardening**: hosted identity with MFA for dashboard users, ASVS level 2 review, pen test, DPIA.
3. **Data residency**: storage and DB in a Saudi region; evaluate in-Kingdom inference options for the vision model.
4. **Scale**: move agent runs to a Postgres-backed queue (new ADR), separate Inspection workers.
5. **Model**: collect expert-reviewed findings as a labeled dataset; consider a fine-tuned segmentation model (license-compatible).
6. **Integration**: export findings to the authority's system of record (for example Arches, if they use it).
7. **Success criteria for the pilot**: weekly coverage of every facade, time from damage to report, false-positive rate after expert review, visitor participation rate.

## Must be ready before Nov 18

- [ ] Demo building chosen and permission status recorded
- [ ] 3D capture done and backed up
- [ ] GLB cleaned, compressed (<= 15 MB) and loads in a viewer
- [ ] `facade_map.json` with 4-6 named facades (Arabic + English names, outward azimuth, 4 corners each)
- [ ] One primary baseline photo per facade, frontal, good light
- [ ] 50 test photos taken and labeled in `labels.csv`
- [ ] Official sources (with links) collected for the building, or "none found" recorded
- [ ] Repository created, CI skeleton running, branch protection on
- [ ] VM created, DNS name pointing to it
- [ ] Anthropic, Azure Speech and Sentry keys created with spending limits, stored outside git
- [ ] Data contracts (facade map, Finding, SSE events, Story) agreed by all four
