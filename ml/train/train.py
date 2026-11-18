import argparse
import gc
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from unsloth import FastVisionModel
from unsloth.trainer import UnslothVisionDataCollator

from ml import REPO_ROOT
from ml.eval.evaluate import evaluate_rows
from ml.eval.tags import evaluate_tags
from ml.train.profiles import TrainConfig, fallback_ladder, load_config, pick_profile

GPU_MISSING = (
    "Training needs a CUDA GPU with at least 16 GB (Google Colab L4 or larger). "
    "A laptop is for inference only: see ml/serve/README.md."
)
MAX_NEW_TOKENS = 2048


@dataclass
class TrainedModel:
    config: TrainConfig
    model: Any
    tokenizer: Any
    trainer: Any


def gpu_memory_gb() -> float:
    if not torch.cuda.is_available():
        raise SystemExit(GPU_MISSING)
    return torch.cuda.get_device_properties(0).total_memory / 1024**3


def resolve(path: str) -> Path:
    return REPO_ROOT / path


def read_rows(path: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in resolve(path).read_text().splitlines() if line.strip()]


def with_images(rows: list[dict[str, Any]], config: TrainConfig) -> list[dict[str, Any]]:
    root = resolve(config.data.root)
    return [{"messages": _load_images(row["messages"], root, config.max_image_side)} for row in rows]


def _load_images(messages: list[dict[str, Any]], root: Path, max_side: int) -> list[dict[str, Any]]:
    loaded = []
    for message in messages:
        content = []
        for part in message["content"]:
            if part["type"] == "image":
                content.append({"type": "image", "image": open_image(root / part["image"], max_side)})
            else:
                content.append(part)
        loaded.append({"role": message["role"], "content": content})
    return loaded


def open_image(path: Path, max_side: int) -> Image.Image:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
    rgb.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return rgb


def load_model(config: TrainConfig) -> tuple[Any, Any]:
    model, tokenizer = FastVisionModel.from_pretrained(
        config.model_id,
        load_in_4bit=False,
        use_gradient_checkpointing="unsloth",
        max_seq_length=config.max_seq_length,
    )
    model = FastVisionModel.get_peft_model(
        model,
        finetune_vision_layers=config.lora.finetune_vision_layers,
        finetune_language_layers=config.lora.finetune_language_layers,
        finetune_attention_modules=config.lora.finetune_attention_modules,
        finetune_mlp_modules=config.lora.finetune_mlp_modules,
        r=config.lora.r,
        lora_alpha=config.lora.alpha,
        lora_dropout=config.lora.dropout,
        bias="none",
        random_state=config.train.seed,
        use_rslora=False,
        loftq_config=None,
    )
    return model, tokenizer


def build_trainer(model: Any, tokenizer: Any, config: TrainConfig, train: list, val: list) -> Any:
    from trl import SFTConfig, SFTTrainer

    settings = config.train
    FastVisionModel.for_training(model)
    return SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        data_collator=UnslothVisionDataCollator(model, tokenizer, resize="max"),
        train_dataset=train,
        eval_dataset=val,
        args=SFTConfig(
            output_dir=str(resolve(config.output_dir) / "checkpoints"),
            num_train_epochs=settings.epochs,
            per_device_train_batch_size=settings.per_device_batch,
            per_device_eval_batch_size=1,
            gradient_accumulation_steps=settings.grad_accum,
            learning_rate=settings.learning_rate,
            lr_scheduler_type=settings.lr_scheduler,
            warmup_ratio=settings.warmup_ratio,
            weight_decay=settings.weight_decay,
            max_grad_norm=settings.max_grad_norm,
            optim=settings.optim,
            bf16=True,
            logging_steps=5,
            eval_strategy="epoch",
            save_strategy="epoch",
            save_total_limit=2,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            seed=settings.seed,
            report_to="none",
            remove_unused_columns=False,
            dataset_text_field="",
            dataset_kwargs={"skip_prepare_dataset": True},
            max_length=config.max_seq_length,
        ),
    )


def load_untrained(config: TrainConfig) -> TrainedModel:
    model, tokenizer = load_model(config)
    return TrainedModel(config, model, tokenizer, trainer=None)


def train_once(config: TrainConfig) -> TrainedModel:
    model, tokenizer = load_model(config)
    train = with_images(read_rows(config.data.train), config)
    val = with_images(read_rows(config.data.val), config)
    trainer = build_trainer(model, tokenizer, config, train, val)
    trainer.train()
    return TrainedModel(config, model, tokenizer, trainer)


def train_with_fallback(config: TrainConfig) -> TrainedModel:
    for step in fallback_ladder(config):
        print(f"Training {step.name}: image side {step.max_image_side}px, LoRA r={step.lora.r}")
        try:
            return train_once(step)
        except torch.OutOfMemoryError:
            print(f"Out of GPU memory with {step.name} at {step.max_image_side}px, r={step.lora.r}")
            free_gpu()
    raise SystemExit("Every step of the memory fallback ladder ran out of GPU memory")


def free_gpu() -> None:
    gc.collect()
    torch.cuda.empty_cache()


def save_adapter(trained: TrainedModel) -> Path:
    target = resolve(trained.config.output_dir) / "adapter"
    trained.model.save_pretrained(str(target))
    trained.tokenizer.save_pretrained(str(target))
    return target


def save_merged(trained: TrainedModel) -> Path:
    target = resolve(trained.config.output_dir) / "merged-16bit"
    trained.model.save_pretrained_merged(str(target), trained.tokenizer, save_method="merged_16bit")
    return target


def predict(trained: TrainedModel, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    FastVisionModel.for_inference(trained.model)
    root = resolve(trained.config.data.root)
    answers = []
    for row in rows:
        prompt = row["messages"][:-1]
        image_part = next(p for p in prompt[1]["content"] if p["type"] == "image")
        image = open_image(root / image_part["image"], trained.config.max_image_side)
        answers.append({"id": row["id"], "answer": generate(trained, prompt, image)})
    return answers


def generate(trained: TrainedModel, prompt: list[dict[str, Any]], image: Image.Image) -> str:
    template_messages = [
        {
            "role": m["role"],
            "content": [{"type": p["type"]} if p["type"] == "image" else p for p in m["content"]],
        }
        for m in prompt
    ]
    text = trained.tokenizer.apply_chat_template(
        template_messages, add_generation_prompt=True, enable_thinking=False
    )
    inputs = trained.tokenizer(image, text, add_special_tokens=False, return_tensors="pt").to("cuda")
    output = trained.model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False, use_cache=True)
    new_tokens = output[0][inputs["input_ids"].shape[1] :]
    return str(trained.tokenizer.decode(new_tokens, skip_special_tokens=True))


def _image_slots(content: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"type": "image"} if part["type"] == "image" else part for part in content]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fine-tune Qwen3.5 on Athar wall maps (Colab or a >=22 GB GPU)"
    )
    parser.add_argument("--config", help="config name in ml/configs; picked from GPU memory when left out")
    parser.add_argument("--try-9b", action="store_true", help="use the 9B profile on a ~22 GB GPU")
    parser.add_argument("--skip-merge", action="store_true")
    args = parser.parse_args()
    vram = gpu_memory_gb()
    config = load_config(args.config or pick_profile(vram, try_9b=args.try_9b))
    print(f"GPU memory {vram:.1f} GB, profile {config.name}")
    trained = train_with_fallback(config)
    print(f"Adapter saved to {save_adapter(trained)}")
    if not args.skip_merge:
        print(f"Merged 16-bit model saved to {save_merged(trained)}")
    test_rows = [r for r in read_rows(trained.config.data.test) if r["task"] == "wall_map"]
    report = evaluate_rows(test_rows, predict(trained, test_rows))
    public_rows = read_rows(trained.config.data.public_test)
    report["public_tags"] = evaluate_tags(public_rows, predict(trained, public_rows))
    metrics_path = resolve(trained.config.output_dir) / "metrics.json"
    metrics_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Test metrics saved to {metrics_path}")


if __name__ == "__main__":
    main()
