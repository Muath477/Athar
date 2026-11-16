# ADR-016: Changes made while building Round 1

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

Building Stage 8 turned up places where the plan in 03-architecture and the earlier ADRs did not hold. This record lists each change so the plan and the code agree. The earlier documents are corrected where the change is small; this file is the full list.

## Decisions

| Area | Plan said | Built | Why |
|---|---|---|---|
| Lighting flag (ADR-005, §9) | chroma shift < 6, structure correlation > 0.8 | chroma < 10, structure > 0.6 | The demo shadow scored chroma 6.9 and structure 0.69; the demo crack scored structure 0.07. Values come from the synthetic demo pack only and must be re-measured on real photos (TBD). `uv run python -m eval.run` prints them. |
| pgvector (ADR-004) | apt package on the PostGIS image | Compiled extension copied from `pgvector/pgvector:0.8.7-pg18-trixie` (same Debian and PG major) | No apt step, smaller image. The image runs as the `postgres` user. The first migration also creates both extensions so a fresh database (for example the test database) works. |
| Face blur model (ADR-015) | YuNet from opencv_zoo | Same model, about 232 KB, downloaded at image build with a pinned SHA-256 | The file is not committed. |
| Azure TTS (ADR-010) | azure-cognitiveservices-speech SDK | REST call (SSML, `audio-24khz-48kbitrate-mono-mp3`) through httpx with a 10 s timeout and one retry | The SDK ships a native library and adds nothing for one request type; REST keeps the image small and uses the shared timeout policy. |
| LLM tracing (ADR-014) | Langfuse cloud | No Langfuse. Every model call is a row in `llm_calls` (agent, model, tokens, cost, latency, observation id); `/admin/costs` reads it. Sentry and structlog stay. | Prompts never leave the VM except to the model provider, and one fewer key to manage for the demo. Langfuse can be added behind the same recording wrapper later. |
| Frontend Sentry | `@sentry/nextjs` | Not added in Round 1 | Time; the API has Sentry. |
| Module graph (§2) | missions depends on sites, verification | missions also reads capture (last usable photo per facade) | Coverage needs photo dates. Enforced by import-linter. |
| Verification facade | `verify(run)` | `record_regions(..., regions: list[RegionEvidence])` | The agent builds the evidence from the inspection run, so verification does not import inspection types. |
| Independent confirmations (§9) | count of `finding_confirmations` rows, unique per passport | count of distinct contributors including the first photo; a contributor is the passport id, or the photo hash when there is no passport | A visitor without a passport still counts once per distinct photo, and one visitor never confirms their own finding twice. |
| Public routes (§5) | `GET /sites/{id}` inspector+ | `GET /sites/nearby`, `GET /sites/{id}` and `GET /facades/{id}/baseline` are public | The visitor app needs the facade list and the baseline overlay for the retake guide. Baselines are photos the authority publishes, not visitor data. |
| Review queue path | `GET /reviews/queue` | `GET /review-queue` | Simpler; no pagination needed at demo size. |
| Photo visibility | same passport or dashboard user | A photo sent with a passport is visible only with that passport token (or to dashboard users through findings) | Stops one visitor reading another's run by guessing an id. |
| Model outage | Haiku once, then expert queue | Regions the model could not judge go to the expert queue as `unknown` with `model_unavailable`; the plan falls back to the fixed order; the story falls back to verbatim quotes from official sources or no story | Nothing reaches the map or a visitor without evidence. |
| Server-side fallback | not planned | Sonnet 5.5 calls use the server-side fallback beta (`fallbacks="default"`) | If Sonnet declines a request, the API retries it on a fallback model inside the same call. |

## Consequences

- The tuned lighting thresholds are only as good as the four synthetic demo photos; re-run the evaluation on the real baseline set before the demo.
- Without Langfuse there is no trace UI; the `llm_calls` table and structured logs are the record.

## Versions

Checked 2026-11-16: GitHub Actions `actions/checkout` v7.0.1, `actions/setup-python` v7.1.0, `actions/setup-node` v7.1.0 (tags read with `git ls-remote`, pinned by commit SHA). Docker Hub: `zricethezav/gitleaks:v8.30.1`, `semgrep/semgrep:1.185.0`, `aquasec/trivy:0.76.2`, `minlag/mermaid-cli:12.0.1`.
