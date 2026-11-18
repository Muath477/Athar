# Serving the damage model

Training runs only on Colab (see `ml/notebooks/train_qwen35_damage.ipynb`). Serving runs anywhere that can
answer OpenAI-compatible `POST /v1/chat/completions` with an image. The backend talks to it through
`QwenVisionDetector`:

| setting | default | meaning |
|---|---|---|
| `SADU_DAMAGE_DETECTOR` | `claude` | set to `qwen` to use the own model |
| `SADU_QWEN_URL` | `http://localhost:8080/v1` | llama-server on the same machine |
| `SADU_QWEN_MODEL` | `athar-damage` | model name used until a version is activated in `/dashboard/models` |
| `SADU_QWEN_TIMEOUT_S` | `120` | seconds per request; raise it for slow CPUs |
| `SADU_QWEN_JSON_SCHEMA` | `true` | send the answer schema as `response_format` |
| `SADU_QWEN_TOKEN` | empty | bearer token, only if the server checks one |

When a version is active in the registry, its `name` is sent as the request's `model`, so the server's
model alias must match the registered name. The detector disables thinking
(`chat_template_kwargs: {"enable_thinking": false}`), sends temperature 0, asks once more with the error
when the answer is not valid JSON, and marks the map `failed` (the expert maps it by hand) if the second
answer is still invalid, the server is down or the timeout passes. Each map's audit entry records the model
name and version and the prompt version.

## Option 1: the owner's 16 GB laptop with llama.cpp (recommended)

The notebook's last cells produce, in `MyDrive/athar-ml/<profile>/gguf/`:

* `athar-damage-Q4_K_M.gguf`: the language model, 4-bit (default for the laptop)
* `athar-damage-Q8_0.gguf`: 8-bit, closer to the trained weights
* `mmproj-athar-damage-F16.gguf`: the vision projector, needed with either file

Install llama.cpp (a release build from github.com/ggml-org/llama.cpp, `brew install llama.cpp` on macOS, or
build it with CMake), then:

```bash
llama-server \
  -m athar-damage-Q4_K_M.gguf \
  --mmproj mmproj-athar-damage-F16.gguf \
  --alias athar-damage-v1 \
  --host 127.0.0.1 --port 8080 \
  --ctx-size 8192 \
  --jinja --chat-template-kwargs '{"enable_thinking":false}'
```

Add `-ngl 99` when the laptop has a GPU that llama.cpp supports (Metal, CUDA, Vulkan); leave it out for CPU
only. Check it answers:

```bash
curl -s http://127.0.0.1:8080/v1/models
python -m ml.eval.predict --url http://127.0.0.1:8080/v1 --model athar-damage-v1
```

`predict.py` logs the seconds per photo; set `SADU_QWEN_TIMEOUT_S` to about twice the slowest value.

Memory on a 16 GB machine (file sizes are those of the public Qwen3.5 GGUFs, which the fine-tuned export
matches; the totals are estimates that include an 8k context and compute buffers):

| model file | weights | vision projector | expected total | fits 16 GB |
|---|---|---|---|---|
| 4B Q4_K_M (default) | 2.7 GB | 0.67 GB | about 4.5 to 5 GB | yes, with room for the backend and Docker |
| 4B Q8_0 | 4.5 GB | 0.67 GB | about 6.5 to 7 GB | yes |
| 9B Q4_K_M | 5.7 GB | 0.92 GB | about 8 GB | yes, but slow on CPU |
| 9B Q8_0 | 9.5 GB | 0.92 GB | about 11.5 GB | tight next to Postgres and the frontend |

Qwen3.5 uses attention in only 8 of its 32 layers (the rest are Gated DeltaNet), so the context cache stays
small; the image tokens dominate the prompt. If the backend runs in Docker, point it at the host:
`SADU_QWEN_URL=http://host.docker.internal:8080/v1`.

If a llama.cpp build rejects the `response_format` schema, set `SADU_QWEN_JSON_SCHEMA=false`; the detector
still validates every answer and asks for one repair.

## Option 2: Ollama on the laptop (experimental)

Ollama serves the same OpenAI-compatible API on port 11434. Unsloth's Qwen3.5 guide currently reports that
Qwen3.5 GGUFs with a separate `mmproj` file do not load their vision part in Ollama, and Ollama's import
documentation covers only text GGUFs. Use llama-server unless a newer Ollama release confirms vision support
for `qwen35`. To try it:

A `Modelfile` next to the GGUF:

```text
FROM ./athar-damage-Q4_K_M.gguf
PARAMETER temperature 0
```

```bash
ollama create athar-damage-v1 -f Modelfile
ollama run athar-damage-v1 "hello"
```

The text model alone takes about 3 to 4 GB. Recent Ollama versions can also pull a GGUF repository with its projector from the Hugging Face Hub
(`ollama run hf.co/<account>/<repo>:Q4_K_M`) after you push the `gguf/` folder there from the notebook. Then
set `SADU_QWEN_URL=http://localhost:11434/v1` and `SADU_QWEN_MODEL` to the Ollama model name, and send one
test photo with `ml/eval/predict.py`: if the answer ignores the image, vision did not load.

## Option 3: vLLM on a server or cloud GPU

vLLM is for a shared server with a GPU (16 GB or more for the 4B model in bf16), not for the laptop.
Serve the merged 16-bit model the notebook saves:

```bash
uv pip install vllm==0.34.0
vllm serve ml/outputs/qwen35-4b-l4/merged-16bit \
  --served-model-name athar-damage-v1 \
  --max-model-len 8192 \
  --limit-mm-per-prompt '{"image": 1}' \
  --port 8000
```

Then `SADU_QWEN_URL=http://<server>:8000/v1`. vLLM honours `chat_template_kwargs` and the JSON schema in
`response_format`. vLLM can also serve several LoRA adapters on one base
(`--enable-lora --lora-modules athar-damage-v2=<adapter dir>`), which makes activation in the registry a
switch between adapter names; check that your vLLM version supports LoRA for the `qwen3_5` architecture
before relying on it, otherwise serve each merged version under its own name.

## Grid-cell fallback for the existing HTTP detector

If the backend should not be changed, run the bridge in front of any of the servers above. It accepts the
`http_detection` contract (POST a JPEG, receive `{"detections": [{"label", "score", "box", "severity"}]}`
with normalised boxes) and converts each element into boxes, one per line segment for cracks and gullies:

```bash
python -m ml.serve.http_bridge --upstream http://127.0.0.1:8080/v1 --model athar-damage-v1 --port 8090
SADU_DAMAGE_DETECTOR=http_detection SADU_DETECTOR_URL=http://127.0.0.1:8090/
```

The bridge loses the element shapes (the backend rebuilds elements from cells) and the damage class, so the
native `qwen` detector is preferred.
