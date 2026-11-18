# ADR-019: Damage map as a grid on the rectified wall

- Status: Accepted (pending team review)
- Date: 2026-11-18

## Context

The Diriyah criteria ask for one readable map with a clear colour key, and for experts to correct results easily before approving them. Multimodal models classify regions well but draw poor outlines; pixel-accurate segmentation needs a trained model we do not have. Photos are taken at an angle, so the same wall looks different in every photo.

## Decision

1. **Rectify first.** The inspector drags four handles to the wall corners (default: 8% inset). The API warps that quadrilateral to a front-on image whose aspect matches the wall's real width and height (long side 1200 px). Registered facades take their size from the region pack; any other wall needs a name, width and height in metres.
2. **Grid.** Rows default to 8 (`SADU_MAP_ROWS`); columns follow the wall aspect, between 4 and 16, so cells stay close to square. Cells are labelled A1 (top-left) onward; rows are letters from the top, columns numbers from the left.
3. **One damage type per cell**, the strongest by severity then confidence. Sound cells have no row.
4. **Colour by type, strength by severity.** Seven types (crack, plaster loss, moisture, basal erosion, surface erosion, partial collapse, graffiti), each with a fixed colour; watch, moderate and urgent use increasing opacity. The legend shows the damaged area per type in m².
5. **Expert edits cells, then approves.** Corrections are saved together; approval freezes the map. Each new map of the same wall is compared with the last approved one (new, worse, retyped, improved, resolved).
6. **Accuracy is measured, not claimed.** The detector's answer is stored in `model_cells`; for approved maps it is compared cell by cell with the expert's final map (`GET /maps/accuracy`, `uv run python -m eval.score_maps <folder>` for a labelled batch).

## Alternatives

- Free-form polygons from the model: closer to a conservation drawing, but unreliable from a VLM and slow to correct by hand.
- 3D model as the main view: needs a scan of each wall and is harder to read than a front elevation.

## Consequences

- Precision is limited to the cell size (about 0.6 m² on a 10 × 6 m facade). Enough to plan treatment areas and quantities; not a substitute for a measured survey drawing.
- Comparing maps needs the same grid; if a wall's size or rows change, the change list says the maps are not comparable.
- Detection runs inside the request (one model call, about 10 to 30 s with Claude). A background job is a later step if walls get bigger or models slower.
