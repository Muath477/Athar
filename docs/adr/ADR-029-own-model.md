# ADR-029: Athar's own damage model on Qwen3.5

- Status: Accepted (pending team review)
- Date: 2026-11-18

## Context

ADR-018 put damage detection behind the `DamageDetector` port and said we would not train a model. Since
then experts have started approving maps, each one a rectified wall photo with expert-checked elements
(type, shape, severity, class). The owner wants a model the authority owns, trained on those maps, running
without a paid API, with "Qwen 3.1" as the base.

There is no Qwen 3.1 vision model. The current open, natively multimodal small family is **Qwen3.5 Small**:
0.8B, 2B, 4B and 9B, Apache-2.0, published as `Qwen/Qwen3.5-4B` (image-text-to-text, 4.66B parameters
with the vision encoder) and `unsloth/Qwen3.5-4B`, and the same pattern for 2B and 9B. We read "3.1" as
"the current Qwen" and chose Qwen3.5; the request and this mapping are recorded here so nobody looks for a
3.1 checkpoint later.

Hardware: training runs only on Google Colab, on the owner's subscription GPU with 22 GB (an L4, 22.5 GB),
or an A100 when Colab gives one. The owner's own machine has 16 GB and is used for inference only.

## Decision

### Task: a vision-language model that answers in the glossary

The model receives one rectified photo and answers strict JSON:
`{"elements": [{damage_type, geometry, points, severity, damage_class, confidence}]}` with the eight core
glossary types, the geometry each type requires (area, line, point), points in 0..1, and width, depth or
size classes from `mapping/domain/glossary.py`. The prompt, JSON schema and strict parser live once in
`mapping/application/element_prompt.py` and are shared by the backend detector, the dataset builder and
the evaluation, so training targets and production parsing cannot drift.

Why a VLM rather than a segmentation network (YOLO-seg, Mask R-CNN, SegFormer):

| | VLM (Qwen3.5) | segmentation model |
|---|---|---|
| output | the product's elements directly: type, shape, severity, class, confidence | masks per class; severity and class need a second model or rules |
| data needed | learns the format from tens of maps, quality from hundreds | needs pixel masks, which our editor does not produce |
| public data | crack patches and masks used as auxiliary instructions | the same, but no severity anywhere |
| serving | one OpenAI-compatible server (llama.cpp on a laptop, vLLM on a GPU) | a custom inference service |
| weakness | coordinates are coarser than a mask; long outputs cost time | cannot judge severity or "cement repair" context |

The backend rasterises elements onto the wall's grid (`mapping/domain/raster.py`), so the cell map, the
accuracy card and change detection keep working unchanged.

### Model sizes and training method

- Default: **Qwen3.5-4B, bf16 LoRA** with Unsloth (`load_in_4bit=False`,
  `use_gradient_checkpointing="unsloth"`). Unsloth measures about 10 GB for 4B bf16 LoRA, which leaves room
  for image tokens on the L4.
- **No 4-bit QLoRA**: Unsloth's Qwen3.5 guide advises against QLoRA for this family because quantisation
  differences are higher than normal. 4-bit appears only in the GGUF files exported for inference.
- **9B on the L4** is a documented profile (`ml/configs/qwen35_9b_l4.yaml`): batch 1 x 8 accumulation,
  images capped at 672 px, sequence 2048, vision layers frozen. Unsloth measures 22 GB for 9B bf16 LoRA, so
  this is at the edge of 22.5 GB. An A100 (`qwen35_9b_a100`) is the safe choice for 9B.
- Below 16 GB the notebook falls back to 2B.
- The notebook's first cell reads GPU memory and picks the profile: 40 GB or more → 9B, about 22 GB → 4B
  (flag to try 9B), under 16 GB → 2B.
- Hyperparameters: LoRA r=16, alpha=16 (Unsloth's guidance alpha ≥ r), dropout 0, all linear layers; AdamW
  8-bit, peak LR 2e-4 for 4B and 1e-4 for 9B, cosine decay with 3% warm-up, weight decay 0.01, gradient
  clipping 1.0, bf16, 3 epochs with evaluation every epoch and the best checkpoint kept by eval loss.
- Out-of-memory ladder, automatic: smaller images (x0.75 down to 448 px) → LoRA r=8 → the next smaller model.
- Pinned: transformers 5.17.0 (Qwen3.5 needs v5), Unsloth 2026.11.6, TRL 1.15.0, PEFT 0.21.3
  (`ml/requirements-colab.txt`). The first steps are slow while the Mamba-style Triton kernels compile.

### Data

- Main task: expert-approved maps from `GET /api/v1/ml/training-export` (permission `manage_models`), a zip
  of rectified photos and approved elements. Faces are blurred at upload, before storage, so the export never
  holds an unblurred face; no user, reviewer, field-note or visitor data is exported.
- Weak labels (`?weak=true`): draft maps nobody edited, marked `weak`, used for training only, never from a
  held-out site and never from the model's own drafts.
- Public sets as auxiliary instructions: eleven sources with licences checked one by one, nine of them CC
  BY 4.0 and on by default (historical crack photos from a 1340 Cairo mosque, Kasbah of Algiers heritage
  walls, Darbhanga Fort brick masonry, Brickwork Cracks, RFSAT masonry, SDNET2018, Özgenel classification
  and segmentation, the Complex Tunnel Crack Dataset) plus two opt-in sources (Panam City, and BD3 whose
  licence is unclear, so it is excluded from any published model). Non-commercial or no-derivatives sets
  (CODEBRIM, IDEA, and others listed as reviewed and left out) are excluded. `python -m ml.data.collect`
  fetches, extracts and organises them automatically; the full table and every exclusion reason is in
  `ml/data/README.md`.
- **Splits by site**: every map of a site is in one split (80/10/10 by examples, deterministic), so test
  scores measure unseen sites, which is how the model is used.

### Evaluation

`ml/eval/evaluate.py` reports, on the test split: JSON validity rate (first answer, no repair), per-type
precision, recall and F1 at cell level using the backend's `score_maps` after rasterising both the answer and
the approved elements onto each map's grid (the same matching as the product's accuracy card), macro and
micro F1, damaged-versus-sound accuracy, length and area error in metres and m² per type, and a comparison
table against the detector that drafted each test map (normally the hosted grid detector) on the same maps. A version is
activated only when it beats the active detector on that table.

Before that end-task score exists, the notebook runs a cheaper, earlier check on the public auxiliary data:
`ml/eval/tags.py` scores the base model (a fresh LoRA, which equals the base) and the fine-tuned model on
the same held-out `public_test.jsonl` rows, never trained on, so the before/after comparison is honest. Two
independent Colab runs on the same two reachable sources (`brickwork_cracks`, `rfsat_masonry`; the other
seven were not yet fetched in either run) agree: exact match moved from 16.2% to 95.2% in the first run and
from 16.6% to 94.8% in the second, crack F1 from 0.629 to 0.951 in the first and from 0.608 to 0.945 in the
second (precision 58–58.9% → 92.2–93.6%, recall 63.9–67.6% → 95.4–98.1%), with 100% JSON validity before and
after in both. The two runs landing within a point of each other says this is the training method working,
not a lucky seed. It still says nothing about the other seven damage types, which had no example in either
run, or about real walls, since `public_test` is public close-up photos, not Athar's own maps.

The other seven sources were never actually unreachable: `ml.data.fetch` sent Mendeley and USU requests
with Python's default user agent, and both hosts return `403 Forbidden` to that, not to a browser. Two of
the skipped sources (`kasbah_algiers`, `darbhanga_fort`) are already catalogued with `efflorescence` and
`spall` folder labels mapped to `plaster_loss` and `salt_efflorescence`, so this was a fetch bug, not a
missing dataset, for those two damage types specifically. The fix is in; a re-run with all nine default
sources reachable is what would turn that from a claim into a number.

### Serving and selection

- `SADU_DAMAGE_DETECTOR=qwen` selects `QwenVisionDetector`, which calls any OpenAI-compatible
  `/v1/chat/completions` at `SADU_QWEN_URL` (default `http://localhost:8080/v1`, llama-server) with the image
  as a data URL, thinking disabled, temperature 0 and the JSON schema as `response_format`. Timeout
  `SADU_QWEN_TIMEOUT_S`, default 120 s for CPU or small-GPU inference. One repair request on invalid JSON;
  after that, or on timeout or outage, the map is saved as `failed` and the expert maps it by hand.
- Laptop (16 GB): llama.cpp `llama-server` with the Q4_K_M GGUF (2.7 GB) and the F16 `mmproj` projector
  (0.67 GB), about 5 GB in use; Q8_0 also fits. Ollama is documented as experimental because Qwen3.5's
  separate projector does not load there yet. vLLM is the server or cloud option.
- The registry (`ml_models`, `/ml/models`, `/dashboard/models`) holds versions with metrics. Activating one
  retires the previous; the active version's name becomes the request's `model`, so switching versions is a
  click once the server knows the name. Every map's audit entry records the model, its version and the
  prompt version.
- `ml/serve/http_bridge.py` exposes the existing `http_detection` contract in front of the model, so a
  deployment that cannot change the backend can still use it.

### Privacy

Training uses only rectified wall photos that went through the upload privacy step (EXIF removed, faces
blurred), only approved or explicitly weak maps, and no visitor or staff identifiers. Weights trained on
authority photos are pushed, if at all, to a private Hub repository. Public datasets keep their attribution
(CC BY 4.0) in the dataset card.

## Alternatives

- Keep the hosted multimodal detector only: no training cost, but no owned model and a running API bill.
- QLoRA 4-bit on 9B: fits the L4 easily, but Unsloth advises against it for Qwen3.5.
- Qwen3-VL 8B: an older, separate vision line; Qwen3.5 is the current natively multimodal family and is
  smaller for the same quality.
- Segmentation model: see the table above.

## Consequences

- The quality ceiling is set by the number and spread of approved maps; the dataset report shows per-type
  counts before each run, and types with few examples (cavity, wall head, cement repair) will lag.
- Width classes in millimetres are hard from a photo alone and are expected to be the weakest field.
- The backend gains `mapping/domain/raster.py`, `element_prompt.py`, `qwen_detector.py`, and a small `models`
  module; ADR-018's port is unchanged apart from `DetectionOutput` now carrying elements, model and prompt
  version.
