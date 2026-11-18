# ADR-022: Show the site in 3D on Google Maps, with directions

- Status: Accepted
- Date: 2026-11-18

## Context

Visitors asked to see the place before they arrive and to know how to reach it. The app already had a three.js model of the facades, but it shows the building alone, not where it stands. The sites table already stores a location point and a boundary polygon for every site.

## Decision

- `GET /sites/{id}` (and the other site responses) return `location` and `boundary` as lat/lon, read from PostGIS.
- A new visitor page, `/sites/[siteId]`, has two views: the site on the Google Maps 3D map (`<gmp-map-3d>` through `@vis.gl/react-google-maps` 1.10.2) and the existing facade model. The 3D view draws the boundary as an extruded polygon that frames the camera, puts a marker on the site, and orbits once unless the visitor prefers reduced motion.
- Directions have two levels:
  1. A Google Maps URL (`/maps/dir/?api=1&destination=…&travelmode=…`). It needs no key, and the visitor's location stays inside Google Maps.
  2. With a key, "draw my route" asks for the location once, calls `Route.computeRoutes` (with `legs` for the steps), and draws the path on the 3D map with its distance and time.
- Once a route is drawn, the visitor can:
  - read the steps in Arabic with a turn arrow each; tapping a step flies the camera to it;
  - watch the route before walking: the camera flies along nine points of the path to the site (hidden when the visitor prefers reduced motion);
  - start tracking: `watchPosition` moves the "you are here" marker, greys out the travelled part, shows the next turn and the distance to it over the map, and can keep the camera behind the visitor. More than 40 m from the path shows "you left the route" with a recompute button. Within 30 m of the site, the page says they arrived and offers to photograph the facade.
- Route progress is pure code (`lib/route-geometry.ts`, `route-progress.ts`): projection onto the path, remaining distance, bearing ahead, current step. Positions never leave the browser except to Google when computing a route.
- The map loads only when the visitor taps "اعرض المجسّم". Each load is billed, and visitors at a heritage site are often on mobile data.
- The key is read at request time on the server (`GOOGLE_MAPS_API_KEY`), so one Docker image works in every environment. It reaches the browser, which the Maps JavaScript API requires, so it must be restricted by HTTP referrer and limited to the Maps JavaScript, Map Tiles and Routes APIs.
- Map colours are read from the theme's CSS variables, so a new visual identity changes the map overlay too.

## Alternatives

- Cesium with Google Photorealistic 3D Tiles: more control, but a heavier bundle and the same tile billing.
- Mapbox GL: no photorealistic buildings, and a second map vendor next to Google directions.
- Embedding the Google Maps iframe: no 3D camera control and no boundary overlay.

## Consequences

- Photorealistic 3D buildings cover only some cities. Where Diriyah is not covered, the 3D map still shows satellite imagery on terrain. The facade model and the directions link work without Google.
- Without a key, the page shows only the facade model and the directions link.
- The 3D map center altitude is measured above sea level, so the camera is framed by the boundary polygon (`autofitsCamera`) instead of by a fixed altitude.
