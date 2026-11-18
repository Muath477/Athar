from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class DetectorKind(StrEnum):
    CLAUDE = "claude"
    HTTP_DETECTION = "http_detection"
    HTTP_CELL_CLASSIFICATION = "http_cell_classification"
    NONE = "none"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    sadu_env: Environment = Environment.DEV
    sadu_public_origin: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://sadu:dev@localhost:5432/sadu"

    s3_endpoint_url: str = "http://localhost:8333"
    s3_public_endpoint_url: str | None = None
    s3_access_key_id: str = "devkey"
    s3_secret_access_key: SecretStr = SecretStr("devsecret123")
    s3_bucket: str = "sadu"
    s3_region: str = "us-east-1"

    anthropic_api_key: SecretStr | None = None
    sadu_model_main: str = "claude-sonnet-5-5"
    sadu_model_fast: str = "claude-haiku-5-5"
    sadu_daily_llm_budget_usd: float = 10.0

    azure_speech_key: SecretStr | None = None
    azure_speech_region: str | None = None
    sadu_tts_voice: str = "ar-SA-HamedNeural"

    sentry_dsn_api: str | None = None

    sadu_demo_mode: bool = False
    sadu_demo_cache_dir: str = "demo-cache"
    sadu_max_concurrent_runs: int = Field(default=4, ge=1)
    sadu_yunet_model_path: str = "models/face_detection_yunet_2023mar.onnx"
    sadu_region_packs_dir: str = "../region-packs"

    sadu_damage_detector: DetectorKind = DetectorKind.CLAUDE
    sadu_detector_url: str | None = None
    sadu_detector_token: SecretStr | None = None
    sadu_detector_labels: str = ""
    sadu_detector_min_score: float = Field(default=0.35, ge=0.0, le=1.0)
    sadu_detector_timeout_s: float = Field(default=30.0, gt=0)
    sadu_map_rows: int = Field(default=8, ge=2, le=20)
    sadu_treatment_catalog: str | None = None

    @model_validator(mode="after")
    def require_secrets_in_prod(self) -> "Settings":
        if self.sadu_env is not Environment.PROD:
            return self
        missing = [
            name
            for name, value in {
                "ANTHROPIC_API_KEY": self.anthropic_api_key,
                "S3_SECRET_ACCESS_KEY": self.s3_secret_access_key,
            }.items()
            if value is None or not value.get_secret_value()
        ]
        if "dev" in self.database_url.split("@")[0]:
            missing.append("DATABASE_URL (dev password)")
        if missing:
            raise ValueError(f"Missing production settings: {', '.join(missing)}")
        return self

    @property
    def is_prod(self) -> bool:
        return self.sadu_env is Environment.PROD

    @property
    def treatment_catalog_path(self) -> Path:
        if self.sadu_treatment_catalog:
            return Path(self.sadu_treatment_catalog)
        return Path(self.sadu_region_packs_dir) / "treatments" / "earthen-najdi.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
