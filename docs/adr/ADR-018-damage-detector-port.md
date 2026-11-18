# ADR-018: Damage detection behind a port: Claude or a ready model

- Status: Accepted (pending team review)
- Date: 2026-11-18

## Context

We will not train a model. The map needs either a hosted multimodal model (an API) or a ready-made vision model someone else trained (for example a crack detector on Hugging Face, Roboflow, or a small server the team runs). The choice may change during the hackathon, and the judges may ask how a Diriyah-owned model would plug in.

## Decision

`mapping.application.ports.DamageDetector` is the only thing the map flow knows:

```python
class DamageDetector(Protocol):
    name: str
    async def detect(self, request: DetectionInput) -> DetectionOutput: ...
```

`DetectionInput` carries the rectified wall photo, the same photo with the labelled grid drawn on it, its size, and the grid. `DetectionOutput` returns cells (type, severity, confidence), whether the photo is usable, and a one-line Arabic summary.

Four adapters, chosen by `SADU_DAMAGE_DETECTOR`:

| Value | Adapter | Sends | Expects |
|---|---|---|---|
| `claude` (default) | `ClaudeGridDetector` | the labelled grid image, one structured-output call | cell labels with type, severity, confidence |
| `http_detection` | `HttpDetectionModel` | the rectified JPEG as the request body to `SADU_DETECTOR_URL` | Hugging Face object-detection output `[{label, score, box: {xmin, ymin, xmax, ymax}}]` in pixels, or `{"detections": [{label, score, box: [x0, y0, x1, y1] in 0..1, severity?}]}` |
| `http_cell_classification` | `HttpCellClassifier` | one request per grid cell crop (8 in parallel) | Hugging Face image-classification output `[{label, score}]` |
| `none` | `ManualOnly` | nothing | the expert fills the map by hand |

Model labels are mapped with `SADU_DETECTOR_LABELS` (JSON, for example `{"spalling": "plaster_loss", "Positive": "crack", "Negative": "none"}`); a label that already equals a damage type needs no entry. `SADU_DETECTOR_MIN_SCORE` drops weak predictions, and a detection marks a cell only when its box covers at least 15% of that cell. Ready models rarely output severity, so their cells start at `watch` and the expert raises them.

Any adapter failure becomes `DetectorUnavailable`; the map is still saved with `detector_status = failed` and no cells, so the expert can label it by hand. An unusable photo returns `422 photo_unusable` with the retake reason.

## Alternatives

- Call one provider directly from the route: simplest, but every change of model means editing the flow.
- Run a model inside the API container: needs PyTorch or ONNX runtime in the image and a GPU decision; an HTTP endpoint keeps the API image small and lets the model run anywhere.

## Consequences

- Switching between Claude and a ready model is an environment change, not a code change.
- The Claude path is metered in `llm_calls` like other agents; HTTP models are not metered.
- Segmentation masks are not parsed; a segmentation model needs a small wrapper that returns boxes or per-cell labels.
