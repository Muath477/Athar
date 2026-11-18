# Athar's own damage model

Code to train, evaluate and serve a damage model the authority owns: Qwen3.5-4B fine-tuned with bf16 LoRA on expert-approved wall maps. It reads one rectified wall photo and answers with elements in the unified glossary. No model has been trained yet; everything here is ready for the first export of approved maps.

Decision: [ADR-029](../docs/adr/ADR-029-own-model.md). Overview with the full pipeline diagram: [docs/ml/architecture.md](../docs/ml/architecture.md).

## Layout

| Path | What it does |
|---|---|
| [data/README.md](data/README.md) | Dataset card: target format, sources and licences, splits |
| `data/export_athar.py` | Downloads approved maps from `GET /api/v1/ml/training-export` (needs `manage_models`) |
| `data/collect.py` | Lists and organises the licence-checked public sets |
| `data/build_dataset.py` | Builds chat-format train, validation and test files, split by site |
| `configs/` | Training profiles: `qwen35_4b_l4` (default on a 22 GB L4), `qwen35_9b_l4`, `qwen35_9b_a100`, `qwen35_2b_small` |
| `train/` | Profile selection from GPU memory and the training loop |
| [notebooks/train_qwen35_damage.ipynb](notebooks/train_qwen35_damage.ipynb) | The Colab notebook: data, training, evaluation, GGUF export |
| `eval/evaluate.py`, `eval/predict.py` | Cell-level scores with the backend's matching, and predictions from a running server |
| [serve/README.md](serve/README.md) | Serving with `llama-server` on a 16 GB machine (Q4_K_M GGUF plus the vision projector) or vLLM, and the HTTP bridge |
| `requirements-colab.txt` | Pinned training packages for Colab |

## Steps

1. Export approved maps: `python -m ml.data.export_athar --email <model engineer>`.
2. Build the dataset: `python -m ml.data.build_dataset`. Check the per-type counts in its report.
3. Open the notebook on Colab. The first cell reads the GPU and picks the profile; training, evaluation and the GGUF export follow.
4. Serve the GGUF files with `llama-server` (see [serve/README.md](serve/README.md)) and check them with `python -m ml.eval.predict`.
5. Register the version with its metrics on `/dashboard/models` and activate it only if it beats the active detector on the same test maps. Set `SADU_DAMAGE_DETECTOR=qwen` in the API.

Run these from the repository root so `ml` imports as a package.

## Tests

The scripts' tests need no GPU and run with the backend environment, from `backend/`:

```bash
uv run pytest ../ml/tests
```

CI does not run them yet.
