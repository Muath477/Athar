# ADR-012: One Next.js app with visitor and dashboard route groups

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

We need a phone PWA and a laptop dashboard with a 3D viewer, both Arabic-first.

## Decision

Next.js (App Router) + React + strict TypeScript + Tailwind CSS 4, one app with route groups `(visitor)` and `(dashboard)`. The 3D viewer and MapLibre load only in dashboard routes (dynamic import) to keep the PWA small. PWA: web app manifest + a minimal service worker that caches the shell only. `dir="rtl"` by default, logical CSS properties only.

## Alternatives considered

- **Two separate apps**: smaller bundles by construction, but double setup and CI.
- **Vite SPA**: lighter, but no server rendering for the first visitor screen.

## Consequences

- Bundle discipline needed (route-level code splitting, check with the Next.js bundle analyzer).
- TypeScript: npm `latest` is 7.0.2 on 2026-11-16; pin the TypeScript version that `create-next-app` for Next 16.4 installs and record it here (TBD at scaffold time).

## Versions

next 16.4.6 (engines node >= 20.9.0), react 19.3.1, tailwindcss 4.3.5, maplibre-gl 6.18.0, eslint 10.15.0, eslint-config-next 16.4.6 (npm, 2026-11-16). Node image `node:24-alpine`.
