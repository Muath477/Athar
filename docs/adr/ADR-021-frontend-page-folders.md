# ADR-021: Each page keeps its own components

- Status: Accepted
- Date: 2026-11-18

## Context

All components sat in one `src/components/` folder, so changing one page meant searching through components that belong to other pages.

## Decision

Every route folder under `src/app/` has a private `_components/` folder (excluded from routing by Next.js) holding the components only that page uses. The page imports them with relative paths (`./_components/...`). `src/components/` keeps only components shared by more than one page (today: `evidence-panel.tsx`, used by the dashboard and the review queue, and `site-model.tsx`, used by the dashboard and the site page). Shared helpers stay in `src/lib/`.

```
src/app/
  page.tsx                      _components/nearby-missions.tsx
  capture/                      _components/capture-flow.tsx, camera.tsx
  observation/                  _components/observation-progress.tsx, story-view.tsx
  passport/                     _components/passport-view.tsx
  dashboard/                    layout.tsx, _components/dashboard-nav.tsx, dashboard-view.tsx
  dashboard/login/              _components/login-form.tsx
  dashboard/review/             _components/review-queue.tsx
  dashboard/maps/               _components/maps-index.tsx, map-card.tsx, accuracy-card.tsx
  dashboard/maps/new/           _components/new-map-form.tsx, stepper.tsx, corner-picker.tsx,
                                analysis-progress.tsx
  sites/[siteId]/               _components/site-explorer.tsx, view-switch.tsx, place-3d.tsx,
                                route-controls.tsx, use-route-to-site.ts, directions-panel.tsx,
                                footprint-sketch.tsx
  dashboard/maps/[mapId]/       _components/map-editor.tsx, map-toolbar.tsx, layer-controls.tsx,
                                damage-grid.tsx, cell-inspector.tsx, damage-legend.tsx,
                                map-changes.tsx, treatment-plan.tsx
src/components/evidence-panel.tsx, site-model.tsx
src/lib/                        api.ts, maps.ts, labels.ts, damage-palette.ts, plural.ts, ...
```

## Consequences

- A change to one page touches one folder. When a component starts being used by a second page, it moves to `src/components/`.
