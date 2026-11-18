# ADR-023: A site can exist before its facades

- Status: Accepted
- Date: 2026-11-18

## Context

The 3D view and directions need only a site's location and boundary, but the region pack format required a facade map and baseline photos for every site. Facades and baselines for Diriyah need permission and photos from the Diriyah Gate Development Authority, which we do not have yet. The only Diriyah data we can cite is UNESCO's point and area for At-Turaif (property 1329).

## Decision

- `facade_map_file` and `baselines` are optional in a pack. Baselines without a facade map are rejected.
- `region-packs/diriyah` adds At-Turaif District at UNESCO's coordinates. Its boundary is a circle with UNESCO's 28.78 ha area, marked as an approximation in the pack's README.
- When a visitor photographs a site that has no facades, the plan is guide only, without calling the model: the observation is linked to the site, the passport is stamped, and the result links to the site page. No damage comparison runs.
- The site page hides the facade model when there are no facades.

## Consequences

- The demo can show Diriyah on the 3D map and route visitors there today.
- Visitors near At-Turaif get a stamp but no damage check until facades and baselines are added. Adding them later is a pack update, not a code change.
- The approximate boundary decides which photos count as "at At-Turaif" (boundary plus 200 m). Replace it with the official boundary from the nomination file before any real use.
