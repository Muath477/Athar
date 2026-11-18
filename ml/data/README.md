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

The catalogue lives in [`sources.py`](sources.py): licence, page, how each set is fetched and how its folders
map to the glossary. `python -m ml.data.collect list` prints it; `python -m ml.data.collect organise` downloads
the default sources, extracts them under `raw/<key>/extracted/` and writes `public/<key>.jsonl`, printing the
label counts so a layout surprise shows up before training. `--all` adds the opt-in sources, `--only <key>`
picks some, `--keep-going` reports a failed source and moves on.

Fetching needs no browser: direct links (Zenodo, Utah State University), the Mendeley Data public API
(`/public-api/datasets/<id>/files`), and Hugging Face datasets pinned to a commit with `snapshot_download`.
`.rar` archives need `unrar` or 7-Zip (the notebook installs both). Every archive member is checked before
extraction and a path that leaves the folder stops the run.

| key | dataset | licence | surface | labels | maps to | default |
|---|---|---|---|---|---|---|
| historical_cracks_cairo | [Historical-crack18-19](https://data.mendeley.com/datasets/xfk99kpmj9/1), Mosque of Amir Al-Maridani (1340), Cairo | CC BY 4.0 | historic stone and plaster | 757 crack, 3,139 non-crack | `crack`, sound | yes |
| kasbah_algiers | [Surface damage of heritage walls, Kasbah of Algiers](https://data.mendeley.com/datasets/zwshr65gnc/2) | CC BY 4.0 | historic plastered masonry | efflorescence, spall, crack, mold | `salt_efflorescence`, `plaster_loss`, `crack`; mold dropped | yes |
| darbhanga_fort | [Brick masonry damage, Darbhanga Fort](https://data.mendeley.com/datasets/s6t5nn73bm/1) | CC BY 4.0 | historic red brick | crack, spalling, vegetation, background (7,886 images, 768 px) | `crack`, `plaster_loss`, sound; vegetation dropped | yes |
| brickwork_cracks | [Brickwork Cracks Dataset](https://zenodo.org/records/8014150) | CC BY 4.0 | brickwork | 350 crack, 350 sound | `crack`, sound | yes |
| rfsat_masonry | [Crack Detection in Images of Bricks and Masonry](https://zenodo.org/records/6870108) | CC BY 4.0 | bricks and masonry | positive / negative (about 80,000 patches) | `crack`, sound | yes |
| sdnet2018 | [SDNET2018](https://digitalcommons.usu.edu/all_datasets/48), DOI 10.15142/T3TD19 | CC BY 4.0 | concrete decks, walls, pavements | cracked / uncracked (56,000+ patches) | `crack`, sound | yes |
| ozgenel_classification | [Concrete Crack Images for Classification](https://data.mendeley.com/datasets/5y9wdsg2zt/2) | CC BY 4.0 | concrete | positive / negative (40,000 patches) | `crack`, sound | yes |
| ozgenel_segmentation | [Concrete Crack Segmentation Dataset](https://data.mendeley.com/datasets/jwsn7tfbrp/1) | CC BY 4.0 | concrete | 458 images with crack masks | `crack` lines (mask to polyline) | yes |
| ctcd_tunnel_cracks | [Complex Tunnel Crack Dataset](https://huggingface.co/datasets/shiweiluo99/tunnel-crack-segmentation-dataset), revision `d7f60e6` | CC BY 4.0 | tunnel lining | 292 images with crack masks | `crack` lines | yes |
| panam_city | [Historic wall images of Panam City](https://data.mendeley.com/datasets/6h6rhwfkpy/1) | CC BY 4.0 | historic lime-plastered brick | artistic, corroded brick, corroded plaster, fungus, living plant | `plaster_loss`, sound (artistic); others dropped | opt-in (2.7 GB) |
| bd3_building_defects | [BD3 on the Hub](https://huggingface.co/datasets/chandrabhuma/building_defect_vqa), revision `520fef0` | unclear | concrete and stone buildings | algae, major/minor crack, peeling, plain, spalling, stain | `crack`, `plaster_loss`, sound; algae and stain dropped | opt-in, research only |

Classes outside the glossary are dropped, never called sound: a mouldy wall may still be cracked. Folder names
are matched after lower-casing and treating spaces, hyphens and underscores alike, deepest folder first, so
`Non-Crack` is sound and `Crack` is `crack`. Images in folders that match nothing are skipped; if a source's
counts come out empty, its layout changed and its `folder_labels` need a look.

Known limits of the fetch:

* The Kasbah of Algiers record exposes `test_multi_label.zip` through the public API; the full training crops
  may need a browser download into `raw/kasbah_algiers/`.
* Darbhanga Fort's images are counted only if the damaged images sit in per-class folders.
* BD3's original repository states no licence, so it stays opt-in and out of any published model.

Reviewed and left out:

| dataset | why |
|---|---|
| [CODEBRIM](https://zenodo.org/records/2620293), DeepCrack | non-commercial licences, which do not fit a product delivered to heritage authorities |
| [IDEA earthquake damage](https://zenodo.org/records/15120522) | CC BY-NC-ND 4.0: no derivatives and non-commercial |
| StructDamage (arXiv 2603.10484) | the paper says CC BY 4.0 but names no download, and it repackages 32 sets with mixed terms |
| [Shanhaiguan Great Wall surface damage](https://data.mendeley.com/datasets/tv9kxjp8z2) | CC BY 4.0, but the record publishes only spreadsheets, no images |
| [Synthetic masonry surfaces](https://huggingface.co/datasets/DavidHidde/synthetic-masonry-surfaces) | GPL-3.0 on data, unclear for model weights |
| [fcakyon/crack-instance-segmentation](https://huggingface.co/datasets/fcakyon/crack-instance-segmentation) | no licence stated |
| [LibreYOLO/wall-damage](https://huggingface.co/datasets/LibreYOLO/wall-damage) | its classes are wall rotation levels, not surface damage |
| [mohammadnajeeb/concrete_crack_images](https://huggingface.co/datasets/mohammadnajeeb/concrete_crack_images) | an unattributed copy of Özgenel; the original is fetched instead |

No public dataset of Najdi mud-brick or adobe wall damage with an open licence was found. Basal erosion,
rain gullies, cavities, wall heads and cement repairs are learned from Athar maps only, so their quality
depends on how many approved maps exist.

Each public set is capped (default 1,500 examples, half sound and half damaged). The public tasks use their own
short instructions (`patch_tags`, `crack_lines`) so they teach visual concepts without teaching the wall-map
answer format wrong things such as severity.

Attribution: keep this table with any model card you publish; CC BY 4.0 requires naming the authors and
the licence.

## Splits

`python -m ml.data.build_dataset` writes `build/train.jsonl`, `build/val.jsonl`, `build/test.jsonl` and
`build/public_test.jsonl`. It also runs with no Athar export yet, on the public sets alone:

* Splits are by **site** (falling back to facade, then map, for maps without a site). Every photo of a site
  lands in one split, so the test score measures walls the model has never seen.
* Sites are assigned deterministically (seeded hash order, then the split furthest from its 80/10/10
  target), so re-running with more maps keeps earlier sites where they were unless the seed changes.
* Public close-ups (`patch_tags`) are split by a seeded hash of the image: 10% go to `public_test.jsonl` and
  are never trained on, 5% go to validation while there are no Athar validation maps (otherwise to training),
  the rest to training. Crack-line tasks stay in training. The notebook scores `public_test` on the base model
  before training and on the fine-tuned model after it, with the same rows.
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
