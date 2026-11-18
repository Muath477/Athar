# ADR-025: Screen site surroundings from Sentinel-2 and send alerts to the ground

- Status: Accepted
- Date: 2026-11-18

## Context

The Heritage Commission challenge asks how heritage can be seen from space. Field inspection covers a few walls a week. Most damage to Riyadh-region sites starts around them: new roads and buildings at the edge, digging, standing water after rain, palm groves cleared, sand drifting in. These show at 10 m resolution. Cracks, roof loss and wall collapse do not. Prior work agrees: EAMENA's change detection works for regional screening but raises false alarms from sand, shadows and misregistration, and Tapete & Cigna (2018) place Sentinel-2 as a screening layer that inspectors or very-high-resolution imagery confirm.

## Decision

- A `watch` module screens each site and a 150 m ring around its boundary. It produces a risk level, not a damage verdict.
- **Source.** The source is Sentinel-2 L2A Collection 1 (`sentinel-2-c1-l2a`) from Element 84 Earth Search: a STAC search plus windowed reads of public COGs with rasterio.
  - Reflectance is `DN × 0.0001 − 0.1`, from the asset metadata.
  - Clear pixels are SCL classes 4, 5 and 6.
  - The source sits behind a `SceneSource` port. A sample source makes labelled synthetic scenes for demos, tests and machines without internet. `SADU_SCENE_SOURCE` picks `earth_search`, `sample` or `none`.
- **Composites.**
  - Baseline: the per-pixel median and robust spread (1.4826 × MAD) of up to 16 scenes over the 365 days ending the day before the recent window. The year is cut into 16 equal slices and each slice gives its clearest scene, so the dry season cannot crowd out winter. Each pixel needs at least 8 clear looks.
  - Recent: the clearest scene from each of 6 slices of the last 30 days, with at least 3 clear looks per pixel.
  - If less than 60 % of the watched area is valid, the scan reports `insufficient_data` rather than a verdict.
- **Change.**
  - A pixel changed when the RMS of per-band z-scores against the baseline spread reaches 3. Only clusters of 3 or more 8-connected pixels count.
  - Only changed pixels are labelled. Each gets one label, first match wins:
    1. Water: MNDWI rises above 0 from below −0.1.
    2. Vegetation loss: NDVI was at least 0.3 and drops by 0.15 and 30 %.
    3. Construction: NDBI rises by 0.10, or the surface darkens to asphalt.
    4. Sand: TGSI rises by 0.05 while brightness rises.
    5. Earthworks: any other change.
  - Every threshold is a starting value to tune on the backtest. None comes from a paper.
- **Risk.**
  - Each signal is weighted by threat and zone, with inside counting double the ring.
  - The score is capped at 100. Levels are watch at 10, moderate at 30 and urgent at 60.
  - Ranking puts the level first. Within a level, World Heritage properties get a 1.25 priority boost.
- **Action.**
  - An inspector can request a ground check on the latest completed scan if it has signals. It opens up to three `satellite_alert` photo missions on the site's facades, which are high priority for visitors nearby. Facades without a baseline photo are skipped.
  - If no facade can take a mission, the dashboard tells the inspector a site visit is needed. No visit record is created yet.
  - Experts acknowledge alerts. Scans, ground checks and acknowledgements are audited.
- **Schedule.** Scans run in a background queue (two at a time, one per site), outside any database transaction while imagery is read. "Scan now" returns 202 and the dashboard polls. A loop queues sites whose last completed scan is older than `SADU_WATCH_INTERVAL_H` (default weekly), and retries a failed scan after 6 hours. Setting the interval to 0 turns the loop off.
- **Failures.** A scan that could not reach the imagery or had too few clear looks is stored, but the ranking and the site page keep showing the last completed scan and mention the failed attempt next to it.
- **Evidence.**
  - Each scan stores before, after and change PNGs, with the site outline and the ring.
  - The dashboard shows them with a before/after slider and credits "Contains modified Copernicus Sentinel data".
- **Security.**
  - rasterio 1.5.2 bundles GDAL 3.12.2, which has open CVEs in its HDF-EOS, netCDF and MiraMon drivers and the vendored zlib `infback9`.
  - Reads are limited to the GTiff driver, HTTPS hrefs on the Earth Search Sentinel bucket and `.tif` paths. Directory listing on open is off.
  - The catalog's JSON is validated field by field before use.

## Alternatives

- **Google Earth Engine:** has more data and tools, but needs an account and a service key, its terms limit commercial use, and our code would depend on a remote API we cannot test offline.
- **Copernicus Data Space (openEO, Sentinel Hub):** official, but OAuth and quotas add setup for a hackathon. It stays possible later as another `SceneSource`.
- **Commercial very-high-resolution imagery:** the only way to see walls from space. Cost and licensing put it out of Round 1, and the ground missions cover the walls instead.
- **Sentinel-1 coherence:** works through dust and cloud and catches surface disturbance. It needs SLC/InSAR processing and says only that something changed. Deferred to v2.

## Consequences

- The API image gains rasterio and scipy. The bundled GDAL must be watched for a release with 3.13 or later.
- The 10 m grid misses anything smaller than about 20 × 20 m, and large properties (Al-Faw is 4,848 ha) are screened only around their core point. The README of each pack says so.
- **False alarms:** seasonal greening, wet soil after rain and misregistration will raise some.
  - The sample source and the unit tests do not measure this.
  - `eval/backtest_watch.py` replays past dates per site and writes an alert table with evidence images. Reviewers fill in `truth` from historical imagery, and `score` computes precision.
  - The pass mark from the market review is precision of at least 0.6 with at least 3 real changes. Until a backtest passes, alerts are framed as "needs a visit".
- `.github/workflows/space-watch-live.yml` runs the live source by hand, because the CI network and our sandbox cannot reach the imagery.
