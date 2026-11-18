# Dataset card: Athar wall damage maps

This folder builds the training data for Athar's own damage model. Everything here is produced by scripts;
the folders `raw/`, `public/`, `athar/` and `build/` are created locally and are not committed.

## What the model learns

Input: one rectified wall photo (the wall fills the frame, as produced by the backend's `rectify_wall`).
Output: strict JSON in the backend's glossary, defined once in
`backend/src/sadu/modules/mapping/application/element_prompt.py`:

```json
{"elements": [
  {"damage_type": "crack", "geometry": "line", "points": [[0.12, 0.30], [0.15, 0.62]],
   "severity": "moderate", "damage_class": "from_1_to_5mm", "confidence": "high"}
]}
```

| damage_type | geometry | damage_class |
|---|---|---|
| plaster_loss | area | null |
| crack | line | width: under_1mm, from_1_to_5mm, over_5mm |
| basal_erosion | area | depth: shallow, medium, deep |
| rain_gully | line | depth: shallow, medium, deep |
| salt_efflorescence | area | null |
| cavity | point | size: small, medium, large |
| wall_head | area | null |
| cement_repair | area | null |

Points are fractions of the photo (0 to 1, origin top left). Severity is `watch`, `moderate` or `urgent`;
confidence is `low`, `medium` or `high`. The backend rasterises the elements onto the wall's grid, so the
same answer also feeds the cell-based map, the accuracy card and the `http_detection` bridge
(`ml/serve/http_bridge.py`).

## Sources

### 1. Athar expert-approved maps (main task)

`python -m ml.data.export_athar --email <model engineer>` calls `GET /api/v1/ml/training-export`
(permission `manage_models`) and unpacks:

* `images/<map_id>.jpg`: the rectified wall photo. Faces were blurred when the photo was uploaded, before it
  was stored, so no export holds an unblurred face.
* `manifest.jsonl`: one line per approved map with `site_id`, `facade_id`, wall size, grid, the approved
  elements, the first detector's name, status and cells, and `label_quality`.
* No user ids, reviewer names, field notes or visitor data are exported.

`--weak` adds draft maps whose elements nobody edited yet, marked `label_quality: weak`. They are used
only for training, never from a held-out site, and never when the draft came from the Qwen detector itself.

### 2. Public datasets (auxiliary tasks)

`python -m ml.data.collect list` prints the sources; `python -m ml.data.collect organise` extracts each
archive under `raw/<key>/` and writes `public/<key>.jsonl`, printing the label counts so a layout surprise
shows up before training. Zenodo files download directly; the Mendeley and USU pages need a browser
download, after which the archive goes in `raw/<key>/<archive name>`.

| key | dataset | licence | size | labels | maps to | cannot teach |
|---|---|---|---|---|---|---|
| sdnet2018 | [SDNET2018](https://digitalcommons.usu.edu/all_datasets/48), Utah State University, DOI 10.15142/T3TD19 | CC BY 4.0 | 56,000+ patches of 256x256 px from bridge decks, walls and pavements, 503.8 MB | cracked / uncracked per patch | `crack` tag | geometry, severity, any earthen texture |
| ozgenel_classification | [Concrete Crack Images for Classification](https://data.mendeley.com/datasets/5y9wdsg2zt/2), Özgenel, DOI 10.17632/5y9wdsg2zt.2 | CC BY 4.0 | 40,000 patches of 227x227 px | positive / negative | `crack` tag | geometry, width class, mud-brick surfaces |
| ozgenel_segmentation | [Concrete Crack Segmentation Dataset](https://data.mendeley.com/datasets/jwsn7tfbrp/1), DOI 10.17632/jwsn7tfbrp.1 | CC BY 4.0 | 458 high-resolution images with masks | binary crack masks | `crack` lines (mask to polyline) | width in mm (no scale), severity |
| rfsat_masonry | [Crack Detection in Images of Bricks and Masonry](https://zenodo.org/records/6870108), RFSAT, DOI 10.5281/zenodo.6870108 | CC BY 4.0 | about 80,000 patches, 382.5 MB | positive / negative | `crack` tag | geometry, earthen plaster |
| kasbah_algiers | [Surface damage of heritage walls, Kasbah of Algiers](https://data.mendeley.com/datasets/zwshr65gnc/2), DOI 10.17632/zwshr65gnc.2 | CC BY 4.0 | 2,674 crops from 224 to 1500 px | multi-label: efflorescence, spall, crack, mold | `salt_efflorescence`, `plaster_loss` (spall), `crack`; mold dropped | geometry, Najdi mud-brick, severity |

Reviewed and left out:

| dataset | why |
|---|---|
| [CODEBRIM](https://zenodo.org/records/2620293) | licence is non-commercial, which does not fit a product delivered to heritage authorities |
| [IDEA earthquake damage](https://zenodo.org/records/15120522) | CC BY-NC-ND 4.0: no derivatives and non-commercial |
| StructDamage (arXiv 2603.10484) | licence not stated; it re-packages 32 other datasets with mixed terms |

No public dataset of Najdi mud-brick or adobe wall damage with an open licence was found. Basal erosion,
rain gullies, cavities, wall heads and cement repairs are learned from Athar maps only, so their quality
depends on how many approved maps exist.

Each public set is capped (default 1,500 examples, half sound and half damaged) and goes to the training
split only. The public tasks use their own short instructions (`patch_tags`, `crack_lines`) so they teach
visual concepts without teaching the wall-map answer format wrong things such as severity.

Attribution: keep this table with any model card you publish; CC BY 4.0 requires naming the authors and
the licence.

## Splits

`python -m ml.data.build_dataset` writes `build/train.jsonl`, `build/val.jsonl`, `build/test.jsonl`:

* Splits are by **site** (falling back to facade, then map, for maps without a site). Every photo of a site
  lands in one split, so the test score measures walls the model has never seen.
* Sites are assigned deterministically (seeded hash order, then the split furthest from its 80/10/10
  target), so re-running with more maps keeps earlier sites where they were unless the seed changes.
* `build/report.md` and `report.json` list examples, sites and elements per damage type for each split.
  Read it before training: a class with no test elements has no test score.

Each line is a chat conversation in the format Unsloth's vision collator expects (system text, user image
path plus instruction, assistant JSON) with a `meta` block used only by evaluation.

## Known gaps

* Severity and damage class come only from Athar experts; public sets carry none.
* Width classes in millimetres depend on the wall's real size and photo resolution; the model sees only the
  photo, so expect the width class to be the weakest field.
* A few dozen approved maps are enough to learn the answer format, not to be accurate. The accuracy card
  and the comparison table in `ml/eval` decide when a version is good enough to activate.
