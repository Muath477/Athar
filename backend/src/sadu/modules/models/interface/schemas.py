from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from sadu.modules.models import api as models

NAME_PATTERN = r"^[a-z0-9][a-z0-9._-]*$"


class ModelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120, pattern=NAME_PATTERN)
    version: str = Field(min_length=1, max_length=40, pattern=NAME_PATTERN)
    base_model: str = Field(min_length=2, max_length=200)
    adapter_uri: str = Field(min_length=2, max_length=500)
    metrics: dict[str, Any] = Field(default_factory=dict, max_length=60)


class ModelOut(BaseModel):
    id: UUID
    name: str
    version: str
    base_model: str
    adapter_uri: str
    metrics: dict[str, Any]
    status: models.ModelStatus
    created_at: datetime
    activated_at: datetime | None


def model_out(view: models.ModelView) -> ModelOut:
    return ModelOut(
        id=view.id,
        name=view.name,
        version=view.version,
        base_model=view.base_model,
        adapter_uri=view.adapter_uri,
        metrics=view.metrics,
        status=view.status,
        created_at=view.created_at,
        activated_at=view.activated_at,
    )
