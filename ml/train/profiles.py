from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"
A100_VRAM_GB = 40
NINE_B_MIN_VRAM_GB = 20
FOUR_B_MIN_VRAM_GB = 16
MIN_IMAGE_SIDE = 448
IMAGE_STEP = 0.75
SMALLER_MODEL = {
    "qwen35_9b_a100": "qwen35_4b_l4",
    "qwen35_9b_l4": "qwen35_4b_l4",
    "qwen35_4b_l4": "qwen35_2b_small",
}


@dataclass(frozen=True)
class LoraSettings:
    r: int
    alpha: int
    dropout: float
    finetune_vision_layers: bool
    finetune_language_layers: bool
    finetune_attention_modules: bool
    finetune_mlp_modules: bool


@dataclass(frozen=True)
class TrainSettings:
    epochs: int
    learning_rate: float
    lr_scheduler: str
    warmup_ratio: float
    weight_decay: float
    max_grad_norm: float
    per_device_batch: int
    grad_accum: int
    optim: str
    seed: int


@dataclass(frozen=True)
class DataSettings:
    root: str
    train: str
    val: str
    test: str
    public_test: str = "ml/data/build/public_test.jsonl"


@dataclass(frozen=True)
class TrainConfig:
    key: str
    name: str
    model_id: str
    base_model: str
    min_vram_gb: int
    max_image_side: int
    max_seq_length: int
    lora: LoraSettings
    train: TrainSettings
    data: DataSettings
    output_dir: str

    @property
    def effective_batch(self) -> int:
        return self.train.per_device_batch * self.train.grad_accum


def load_config(key: str) -> TrainConfig:
    raw: dict[str, Any] = yaml.safe_load((CONFIG_DIR / f"{key}.yaml").read_text())
    return TrainConfig(
        key=key,
        name=raw["name"],
        model_id=raw["model_id"],
        base_model=raw["base_model"],
        min_vram_gb=int(raw["min_vram_gb"]),
        max_image_side=int(raw["max_image_side"]),
        max_seq_length=int(raw["max_seq_length"]),
        lora=LoraSettings(**raw["lora"]),
        train=TrainSettings(**raw["train"]),
        data=DataSettings(**raw["data"]),
        output_dir=raw["output_dir"],
    )


def pick_profile(vram_gb: float, *, try_9b: bool = False) -> str:
    if vram_gb >= A100_VRAM_GB:
        return "qwen35_9b_a100"
    if try_9b and vram_gb >= NINE_B_MIN_VRAM_GB:
        return "qwen35_9b_l4"
    if vram_gb >= FOUR_B_MIN_VRAM_GB:
        return "qwen35_4b_l4"
    return "qwen35_2b_small"


def fallback_ladder(config: TrainConfig) -> list[TrainConfig]:
    ladder = [config]
    current = config
    while round(current.max_image_side * IMAGE_STEP) >= MIN_IMAGE_SIDE:
        current = replace(current, max_image_side=_patch_multiple(current.max_image_side * IMAGE_STEP))
        ladder.append(current)
    if current.lora.r > 8:
        current = replace(current, lora=replace(current.lora, r=8, alpha=8))
        ladder.append(current)
    smaller = SMALLER_MODEL.get(config.key)
    if smaller is not None:
        ladder.extend(fallback_ladder(load_config(smaller)))
    return ladder


def _patch_multiple(side: float) -> int:
    return int(side // 32) * 32
