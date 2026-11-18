# Diriyah region pack

One site so far: At-Turaif District (UNESCO World Heritage property 1329).

| Field | Value | Source |
|---|---|---|
| Location | 24.734133, 46.572467 (N24 44 2.88, E46 34 20.88) | [UNESCO World Heritage Centre, property 1329, maps](https://whc.unesco.org/en/list/1329/maps/) |
| Area | 28.78 ha (buffer zone 237.95 ha) | Same page |
| Boundary | **Approximation**: a 24-sided circle of the same area (radius 302.7 m) around the UNESCO point | Generated; replace with the official boundary from the nomination file before any real use |

The site has no facades, baseline photos or story sources yet. Until they are added, a visitor's photo near At-Turaif finds the site, stamps the passport and links to the 3D view and directions, but no damage comparison runs. Facades, baselines and sources need permission and photos from the Diriyah Gate Development Authority.

Import it with:

```
docker compose exec api python -m sadu.cli seed --pack diriyah
```
