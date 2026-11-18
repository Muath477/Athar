from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.mapping import api as mapping
from sadu.modules.models.domain.registry import ModelStatus, can_move
from sadu.modules.models.infrastructure.archive import TrainingArchive, stream_and_remove
from sadu.modules.models.infrastructure.orm import MlModelRow
from sadu.shared.errors import Conflict, NotFound
from sadu.shared.storage import ObjectStore

__all__ = ["ModelStatus"]

EXPORT_FORMAT = "athar-training-export-v1"


@dataclass(frozen=True)
class ModelView:
    id: UUID
    name: str
    version: str
    base_model: str
    adapter_uri: str
    metrics: dict[str, Any]
    status: ModelStatus
    created_at: datetime
    activated_at: datetime | None


@dataclass(frozen=True)
class NewModel:
    name: str
    version: str
    base_model: str
    adapter_uri: str
    metrics: dict[str, Any]


@dataclass(frozen=True)
class TrainingExport:
    chunks: Iterator[bytes]
    examples: int


async def list_models(session: AsyncSession) -> list[ModelView]:
    rows = await session.scalars(select(MlModelRow).order_by(MlModelRow.created_at.desc()))
    return [_view(row) for row in rows]


async def register_model(session: AsyncSession, model: NewModel, created_by: UUID) -> ModelView:
    row = MlModelRow(
        name=model.name,
        version=model.version,
        base_model=model.base_model,
        adapter_uri=model.adapter_uri,
        metrics=model.metrics,
        status=ModelStatus.CANDIDATE,
        created_by=created_by,
    )
    try:
        async with session.begin_nested():
            session.add(row)
    except IntegrityError as error:
        raise Conflict("model_version_exists") from error
    return _view(row)


async def activate_model(session: AsyncSession, model_id: UUID) -> ModelView:
    row = await _row_to_move(session, model_id, ModelStatus.ACTIVE)
    await session.execute(
        update(MlModelRow).where(MlModelRow.status == ModelStatus.ACTIVE).values(status=ModelStatus.RETIRED)
    )
    row.status = ModelStatus.ACTIVE
    row.activated_at = datetime.now(UTC)
    await session.flush()
    return _view(row)


async def retire_model(session: AsyncSession, model_id: UUID) -> ModelView:
    row = await _row_to_move(session, model_id, ModelStatus.RETIRED)
    row.status = ModelStatus.RETIRED
    await session.flush()
    return _view(row)


async def active_model(session: AsyncSession) -> mapping.ModelChoice | None:
    row = await session.scalar(select(MlModelRow).where(MlModelRow.status == ModelStatus.ACTIVE))
    if row is None:
        return None
    return mapping.ModelChoice(row.name, row.version)


async def training_export(session: AsyncSession, store: ObjectStore, *, weak: bool) -> TrainingExport:
    examples = await mapping.approved_examples(session)
    if weak:
        examples += await mapping.weak_examples(session)
    card = {
        "format": EXPORT_FORMAT,
        "exported_at": datetime.now(UTC).isoformat(),
        "examples": len(examples),
        "faces": "blurred when each photo was uploaded",
        "contains": "rectified wall photos, map elements, detector cells; no user or visitor data",
    }
    with TrainingArchive() as archive:
        for example in examples:
            image_name = f"images/{example.map_id}.jpg"
            jpeg = await store.get(example.rectified_key)
            archive.add_example(image_name, jpeg, _record(example, image_name))
        archive.add_card(card)
    return TrainingExport(stream_and_remove(archive.path), len(examples))


def _record(example: mapping.TrainingExample, image_name: str) -> dict[str, Any]:
    return {
        "map_id": str(example.map_id),
        "site_id": str(example.site_id) if example.site_id else None,
        "facade_id": str(example.facade_id) if example.facade_id else None,
        "image": image_name,
        "width_m": example.wall.width_m,
        "height_m": example.wall.height_m,
        "rows": example.grid.rows,
        "cols": example.grid.cols,
        "elements": [mapping.element_json(e) for e in example.elements],
        "detector": example.detector,
        "detector_status": example.detector_status.value,
        "detector_cells": [mapping.cell_json(c) for c in example.model_cells],
        "label_quality": example.label_quality.value,
    }


async def _row_to_move(session: AsyncSession, model_id: UUID, target: ModelStatus) -> MlModelRow:
    row = await session.get(MlModelRow, model_id, with_for_update=True)
    if row is None:
        raise NotFound("not_found")
    if not can_move(ModelStatus(row.status), target):
        raise Conflict("model_status_unchanged")
    return row


def _view(row: MlModelRow) -> ModelView:
    return ModelView(
        id=row.id,
        name=row.name,
        version=row.version,
        base_model=row.base_model,
        adapter_uri=row.adapter_uri,
        metrics=dict(row.metrics or {}),
        status=ModelStatus(row.status),
        created_at=row.created_at,
        activated_at=row.activated_at,
    )
