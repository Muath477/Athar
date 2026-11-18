# ADR-026: The Diriyah ten-step workflow, the unified glossary and role permissions

- Status: Accepted
- Date: 2026-11-18

## Context

At the challenge deep dive, the Diriyah Gate Development Authority presented what it expects from the agent. Their slides set out:

- **A ten-step procedure map:** photo check, privacy, damage type and place, a confidence gate that consults the specialist, treatments from the approved library, materials and tools with where they go, a unified map and table, specialist review, approval, and approved outputs with a correction log.
- **A glossary of six damage types, each with its own geometry:**
  - Plaster loss: an area in m².
  - Cracks: a line, with length in m and a width class (under 1 mm, 1 to 5 mm, over 5 mm).
  - Basal erosion: an area, with extent and a depth class.
  - Rain gullies: a line, with length and depth.
  - Salt efflorescence: the affected area.
  - Holes and burrows: points, with count and size.
- **Per-element records:** every element carries the wall, the survey date, who prepared it (person or model) and the severity.
- **A treatment table:** with materials and tools, marked as indicative. No cement, rebar or other incompatible modern materials. Structural cracks go to an engineer.
- **Three users:** the restoration specialist, the field surveyor and the site manager. The site manager plans maintenance and budgets and prepares the periodic UNESCO reports.
- **Five rules:** a human in the loop, show uncertainty and never fill in guesses, one glossary, no touching the fabric (and field photography only with the authority's permit), and no treatment approved without a field inspection.

Athar had a grid of cells with seven damage types, approval right after expert corrections, three roles in strict order, and visitor photo missions on any site.

## Decision

- **Glossary.** `mapping/domain/glossary.py` holds the unified glossary.
  - It covers the six brief types plus wall heads and earlier cement repairs (both from their treatment table).
  - The four older Athar types are kept as additional types.
  - Colours follow the brief's map. The dashboard palette mirrors the backend, and a test enforces this.
- **Map elements.**
  - A map is now a list of elements: polygons, polylines or points in wall-relative coordinates.
  - Elements are measured in metres from the wall size: area, length and count.
  - Each element carries an optional class allowed by its type, a severity, a confidence and its source.
  - The model still answers on the grid. Connected cells of one type become one element: the exact outline of the patch for areas, a path through cell centres for lines (diagonal neighbours count, so a stepped crack stays one line), and one point per cell for holes. The specialist then changes an element's type, severity or class, confirms it, deletes it, or draws a new one. Changing a shape means deleting it and drawing it again, so the log keeps both versions. Once elements are edited by hand, grid corrections are refused (409) so they cannot overwrite those edits.
- **Edits.** Every element edit is logged with before, after, editor and time. The log is shown on the map and counted in the PDF.
- **Treatment plans.** Plans are built per element. Each plan item lists the elements and reference cells it applies to ("where on the facade"). Lines and points use a nominal footprint (0.1 m band, 0.04 m² per hole) for material quantities, and the quantities are labelled as estimates.
- **The ten steps.** They are computed from the map's state and shown on the map page with actor, state, output and criterion.
  - Step 4 is flagged while low-confidence model elements remain.
  - Step 9 is blocked until a field inspection is recorded.
- **Approval gates.** Approval refuses with `field_inspection_required` until an expert records the field inspection. It refuses with `low_confidence_unreviewed` while any low-confidence model element has not been confirmed, corrected or removed.
- **Roles.**
  - Roles map to explicit permissions:
    - Field surveyor (`inspector`): read and survey.
    - Site manager (`site_manager`): read and manage the site.
    - Restoration specialist (`expert`): read, survey and review.
    - Admin: all permissions.
  - Read routes require `read`, capture routes `survey`, review routes `review`, and site settings `manage_site`.
  - `/auth/me` returns the user's permissions, and the dashboard shows or hides actions from them.
- **Field photography permit.** Each site has a field photography permit, off by default.
  - Visitor missions are created only on permitted sites.
  - A satellite ground check on a site without a permit asks for an inspector visit instead.
  - Site managers switch the permit, and the change is audited.
- **Site condition summary.** `GET /sites/{id}/condition` gives the site manager every wall with its last survey, field inspection, urgent and low-confidence elements, and whether a specialist is needed. It also gives totals by damage type and the materials for approved treatments. The dashboard page prints as the periodic condition report.

## Alternatives

- **Ask the model for polygons directly.** Vision models place coordinates poorly. The grid keeps model answers checkable cell by cell, and accuracy is still scored on the grid.
- **Drop the grid entirely.** The brief asks to link each photo set to the wall's reference grid, so the grid stays as the reference and as the place model accuracy is measured.
- **Keep ordered roles and add site manager in the middle.** A manager would then inherit survey rights they do not need, and a specialist's rights would depend on order rather than intent.

## Consequences

- Existing maps get elements derived from their cells when read. Nothing needs migrating.
- Hulls overstate the area of L-shaped patches until the specialist redraws them. Model elements are dashed until reviewed.
- Sites in the Riyadh pack start without a photography permit. Visitor missions stay off there until the authority grants one.
- The treatment library remains a draft marked as such. The brief's table is cited as indicative.
