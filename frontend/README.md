# Athar web

One Next.js 16 app (React 19, TypeScript strict, Tailwind CSS 4) for visitors and staff. Arabic first, right to left. All data comes from the API under `/api/v1`.

## Run

```bash
npm ci
SADU_API_ORIGIN=http://localhost:8000 npm run dev   # http://localhost:3000
```

In development, `next.config.ts` proxies `/api` to `SADU_API_ORIGIN`. In production Caddy routes `/api` to the API container, so the browser talks to one origin and the session cookie stays `SameSite=Strict`. Set `GOOGLE_MAPS_API_KEY` for the 3D site view and in-app routes.

## Pages

Each route keeps its own components in `_components/` next to `page.tsx` ([ADR-021](../docs/adr/ADR-021-frontend-page-folders.md)).

| Route | Page | Needs |
|---|---|---|
| `/` | Visitor home: start a photo, nearby photo missions, privacy note | |
| `/capture` | Photograph a facade with consent and the baseline overlay | |
| `/observation` | Progress of a visitor photo, the story and the stamp | |
| `/passport` | Visitor passport, delete it and its photos | |
| `/sites/[siteId]` | Site in 3D on Google Maps, directions | |
| `/dashboard/login` | Staff sign-in | |
| `/dashboard` | 3D site with finding pins | `read` |
| `/dashboard/condition` | Site condition summary, photography permit, PDF and CSV | `read`; permit `manage_site`; downloads `export` |
| `/dashboard/watch`, `/dashboard/watch/[siteId]` | Satellite ranking, before/after slider, change map, ground check | `read`; scan and ground check `survey`; acknowledge `review` |
| `/dashboard/maps`, `/dashboard/maps/[mapId]` | Wall maps, ten-step workflow, element editor, field inspection, approval, report | `read`; editing and approval `review` |
| `/dashboard/maps/new` | New map: wall, photo, four corners | `survey` |
| `/dashboard/uploads` | Bulk upload with per-photo progress and facade choice | `survey` |
| `/dashboard/devices` | Camera registry and «التقط الآن» | `read`; changes `manage_devices` |
| `/dashboard/review` | Review queue for visitor findings | `review` |
| `/dashboard/assistant` | «مساعد أثر» chat | `assistant` |
| `/dashboard/users` | Accounts, roles and site scope | `administer` |
| `/dashboard/audit` | Audit log with filters and CSV | `read_audit`; CSV also `export` |
| `/dashboard/models` | Own-model registry, activate and retire | `manage_models` |
| `/dashboard/password` | Change password | any signed-in user |

`src/app/dashboard/_components/dashboard-nav.tsx` hides sections with `can(me, permission)` from `src/lib/api.ts`, and each page shows a plain message when opened without the permission. The API enforces the same rules.

## Identity and primitives

The «حاشية المخطوط» identity is defined in [docs/design/DESIGN.md](../docs/design/DESIGN.md). Read it before adding a colour, font or component.

- Tokens are in `src/app/globals.css`: `sand`, `white`/`surface`, `clay`/`line`, `mud`, `ink`, `sadu` (rubric red), `on-accent`, `watch`, `moderate`, `urgent`, `wall`, mapped to the shadcn variables (`--primary`, `--destructive`, …). Use the token names, never hex values in components.
- Primitives are in `src/components/ui/` (shadcn/ui on Radix, rewritten with logical properties, 2 px radius and 44 px targets): alert-dialog, avatar, badge, button, card, checkbox, dialog, dropdown-menu, input, label, native-select, progress, radio-group, scroll-area, select, separator, sheet, skeleton, sonner, table, tabs, textarea, tooltip.
- Brand components are in `src/components/brand/`: `athar-mark`, `margin-note` (the marginal note for specialist and low-confidence notes) and `severity-label` (urgent always carries text and an icon).
- Fonts are self-hosted in `src/app/fonts/`: Scheherazade New for Arabic, Cormorant Garamond for Latin.
- RTL comes from `<html dir="rtl">` and Radix `Direction.Provider` in `src/components/providers.tsx`. Use `ms`/`me`/`ps`/`pe`/`start`/`end`, Arabic-Indic digits with `toLocaleString("ar-SA")`, counted nouns with `countAr` in `src/lib/plural.ts`, and `<bdi>` for mixed text.
- Loading and errors: `PageSkeleton` and `RetryAlert` in `src/app/_components/page-status.tsx`.

## Tests

```bash
npm run lint && npm run typecheck && npm test && npm run build
```

- Unit tests (Vitest) sit next to the code they test, mostly in `src/lib/*.test.ts`: assistant, directions, elements, governance, ingest, models, plurals, route geometry, watch, and route progress on the site page.
- End-to-end tests (Playwright) in `e2e/` run against the full stack: a phone project for the visitor journey and a desktop project where an expert maps a wall, approves it, downloads the PDF, and screens a site from space.

```bash
npx playwright install chromium
E2E_EXPERT_EMAIL=you@example.com E2E_EXPERT_PASSWORD='…' npm run e2e
```

`E2E_BASE_URL` changes the target (default http://localhost:3000).
