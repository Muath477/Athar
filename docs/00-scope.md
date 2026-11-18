# 00 · Scope and requirements

Status: draft for team review · Written 2026-11-16 · Owner: tech lead

## Assumptions made while writing this

The team was not available to answer questions, so these assumptions are used throughout the docs. Change them here first if they are wrong.

| # | Assumption | Effect if wrong |
|---|---|---|
| A1 | The demo building is one mud-brick building the team can photograph freely and scan before Nov 18 (TBD which one). | Scan and baselines slip into Round 1; demo uses a fallback model. |
| A2 | Claude API budget of about USD 50 for the whole hackathon is available. | Lower budget forces Haiku for more steps and more cached results. |
| A3 | Damage examples come from our own photos of the demo building plus staged changes (chalk marks, removable tape "cracks", printed graffiti on removable sheets), never by damaging anything. | Smaller or less realistic test set. |
| A4 | No interview with the challenge owner is guaranteed. We prepare 5 questions and use any mentor slot. | Business assumptions stay unvalidated in the pitch. |

## 1. Problem, users and success (restated)

Heritage sites in Saudi Arabia are many and spread across 13 regions, and field teams cannot visit them often. Mud-brick buildings degrade fast (cracks, basal erosion, collapse) and encroachments (graffiti, unauthorized building, removed doors or carvings) are caught late. Public reports, where they exist, are a photo with no precise location, no prior state and no severity.
Athar turns visitors into monitors: a visitor photographs a facade and gets a verified story; agents compare the photo with a baseline of the same facade, verify any change with evidence, and pin it on a 3D model in the authority dashboard.
Users: the **inspector** (paying customer, decides interventions), the **visitor** (data source, gets story and passport), the **expert** (reviews medium-confidence findings).
Success for Round 1: detection precision and recall >= 80% on 50 labeled images, pin on the correct facade >= 90%, >= 9 of 10 false reports rejected or sent back, 100% of published findings linked to evidence, and a measurable drop in unsupported story claims with the Verifier on.

## 2. Functional requirements (user stories)

IDs are referenced from the test plan in [07-infra-and-testing.md](07-infra-and-testing.md).

### Visitor

| ID | Story | Acceptance criteria |
|---|---|---|
| V1 | As a visitor I open Athar from a QR code without installing anything. | PWA loads on a mid-range Android phone over 4G in under 3 s (LCP); works in Arabic RTL by default; shows a one-screen consent for camera, location and heading with "allow" and "skip" options. |
| V2 | As a visitor I photograph a wall and the app records where I stood and which way I faced. | Photo, GPS (lat, lon, accuracy) and compass heading are sent only after consent; if location is refused, the visitor picks the site from a list and the photo is still accepted for the story but flagged "no location" for monitoring. |
| V3 | As a visitor on a monitoring mission I see the reference photo as an overlay so I can match the angle. | Overlay opacity adjustable 20-80%; mission shows the facade name and a short instruction; capture button stays enabled (the overlay is guidance, not a gate). |
| V4 | As a visitor I receive the story of the landmark in text and Arabic audio. | Story arrives in under 10 s (cached path under 2 s); every sentence-level claim shows its confidence label and a source link or narrator name; if no verified source exists the app says so; audio plays with an ar-SA voice. |
| V5 | As a visitor I am asked a short question when the app is unsure which facade I photographed. | Question offers 2-4 facade options with thumbnails plus "I'm not sure"; answering resumes processing; no answer within 2 minutes falls back to the best guess with label Unknown for facade. |
| V6 | As a visitor I am asked for another photo when mine is unusable. | Retake request states the reason (blurry, too dark, wrong angle) in Arabic and shows the overlay again. |
| V7 | As a visitor I keep a Athar Passport of my visits and contributions. | Passport is tied to an anonymous device token, lists sites visited and contribution count with status (received, verified, used in a report); visitor can delete the passport and all linked photos with one action. |

### Inspector (heritage authority)

| ID | Story | Acceptance criteria |
|---|---|---|
| I1 | As an inspector I log in to a dashboard. | Email + password, Argon2id hashes, session cookie expires after 8 h of inactivity; 5 failed attempts lock the account for 15 min. |
| I2 | As an inspector I see the 3D model with a colored pin per published finding on its facade. | Green = watch, yellow = moderate, red = urgent; only findings labeled Confirmed or Likely appear; pin is on the correct facade region; model loads in under 5 s on a laptop over 4G. |
| I3 | As an inspector I click a pin and see the evidence. | Panel shows baseline photo, new (aligned) photo, difference overlay, damage type, severity, confidence label, number of independent confirmations, date and the Verifier's rationale. |
| I4 | As an inspector I see a ranked list of findings for the site. | Sorted by severity, then confidence, then recency; filter by facade and label. |
| I5 | As an inspector I see coverage gaps and the missions the agent dispatched. | List of facades with days since last usable photo; active missions with reason and status. |
| I6 (Round 2) | As an inspector I export a restoration report as PDF. | Arabic RTL PDF with site summary, findings by severity with evidence thumbnails and labels. |

### Expert (reviewer)

| ID | Story | Acceptance criteria |
|---|---|---|
| E1 | As an expert I get a queue of findings that need review. | Queue shows findings paused for review with the same evidence as I3. |
| E2 | As an expert I confirm, correct or reject a finding. | Confirm sets label Confirmed; correct allows changing type and severity; reject removes the pin and records a reason; every decision is audit-logged with user and time; the paused agent run resumes after the decision. |

## 3. Non-functional requirements

| Area | Requirement (measurable) |
|---|---|
| Latency | Upload to pin p95 <= 30 s during the demo; story p95 <= 10 s uncached, <= 2 s cached; status updates pushed within 1 s of each agent step. |
| Mobile performance | Visitor PWA JS <= 250 KB gzipped on first load; photo resized on device to max 2048 px long side, JPEG quality 0.85 (about 0.5-1 MB) before upload; works on a mid-range Android phone over 4G. |
| Arabic / RTL | `dir="rtl"` and `lang="ar"` by default; logical CSS properties only (`margin-inline-start`, not `margin-left`); Arabic numerals choice TBD by UX; stories in Modern Standard Arabic; English UI available for judges. |
| Privacy (Saudi PDPL) | Location and heading collected only after explicit consent; EXIF stripped and faces blurred before any photo is stored or sent to the LLM; no visitor account or name; passport token stored hashed; raw GPS kept only on the observation and deleted with it; retention limits in [03-architecture.md §6](03-architecture.md#6-data-architecture). Cross-border transfer to the LLM provider is flagged as an open legal question for a pilot (TBD). |
| Cost | <= USD 0.05 per processed photo (LLM + TTS), counted per observation and shown on an admin page. Estimate in [04-stack.md](04-stack.md#cost-per-photo). |
| Demo reliability | Every external call has a timeout, at most 2 retries with backoff, and a fallback; a "demo mode" serves cached results for the scripted photos when the network fails; a screen recording of the full flow exists before Nov 21. |
| Availability | Single VM, no HA in Round 1. Restart restores in-flight runs from the LangGraph checkpointer. |
| Security | OWASP ASVS level 1 for the dashboard and API; details in [06-security/threat-model.md](06-security/threat-model.md). |

## 4. Out of scope for Round 1

- Building or updating the 3D model from visitor photos.
- AR (anchored overlays in 3D space). The 2D overlay in the camera view is in scope.
- Visitor login or accounts.
- Native mobile apps.
- Training a damage model from scratch. Pretrained models and the multimodal LLM only.
- Heat map, timeline slider, PDF restoration report, national map and UNESCO region packs (all Round 2).
- More than one building, more than one region pack.
- Push notifications to visitors. Missions are shown when a visitor opens the app on site.
- Multi-tenant authority accounts, SSO, payments.
- Offline photo queueing in the PWA (nice to have if time remains).

## 5. Open questions answered with assumptions

| # | Question | Assumed answer for Round 1 | Owner to confirm |
|---|---|---|---|
| 1 | Which mud-brick building can we scan before Nov 18, and do we need permission? | TBD. Pick a building where photography is clearly allowed and that has 4-6 visually distinct facades. Any registered heritage site or one inside a managed district likely needs permission from its operator; we do not assume we have it. If no permission arrives by Nov 17, scan an unregistered mud-brick structure we have the owner's OK for, and say so in the pitch. | UX/Product |
| 2 | Which multimodal model and what API budget? | `claude-sonnet-5-5` for damage judgment and story drafting, `claude-haiku-5-5` for planning, routing and claim checks. Budget about USD 50 total (A2). | AI engineer |
| 3 | Where do labeled damage examples come from? | Our own photos of the demo building: 25 "no change" photos at varied angles and light, 25 with staged reversible changes or real existing damage compared against an older baseline. Open crack datasets are used only to sanity-check prompts, not for training. Exact datasets TBD after license check. | Data scientist |
| 4 | Can someone from the challenge owner be interviewed during the bootcamp? | Unknown. Prepare 5 questions (inspection frequency, current reporting channel, who acts on a report, data-sharing rules, budget owner) and ask any mentor from the track. Until answered, the business model slide marks these as assumptions. | UX/Product |
