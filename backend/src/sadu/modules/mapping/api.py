import asyncio
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.mapping.application.claude_detector import ClaudeGridDetector
from sadu.modules.mapping.application.manual_detector import ManualOnly
from sadu.modules.mapping.application.ports import (
    DamageDetector,
    DetectionInput,
    DetectionOutput,
    DetectorUnavailable,
)
from sadu.modules.mapping.domain.changes import CellChange, ChangeKind, compare_maps
from sadu.modules.mapping.domain.damage_map import (
    MAP_DAMAGE_TYPES,
    CellCorrection,
    CellSource,
    MapCell,
    MapStatus,
    apply_corrections,
    tally_areas,
)
from sadu.modules.mapping.domain.grid import CellRef, Grid, WallSize
from sadu.modules.mapping.domain.palette import DAMAGE_COLORS, SEVERITY_OPACITY
from sadu.modules.mapping.domain.quad import Quad
from sadu.modules.mapping.domain.scoring import MapScore, ScoredPair, TypeScore, score_maps
from sadu.modules.mapping.infrastructure.http_detector import (
    HttpCellClassifier,
    HttpDetectionModel,
    HttpModelClient,
    LabelMap,
)
from sadu.modules.mapping.infrastructure.imaging import RectifiedWall, paint_damage, rectify_wall
from sadu.modules.mapping.infrastructure.orm import DamageMapCellRow, DamageMapRow
from sadu.modules.treatments import api as treatments
from sadu.shared.config import DetectorKind, Settings
from sadu.shared.errors import Conflict, NotFound, SaduError
from sadu.shared.i18n import translate
from sadu.shared.ports.llm import LLMPort
from sadu.shared.storage import ObjectStore, new_object_key
from sadu.shared.vocabulary import DamageType, ModelConfidence, RetakeReason, Severity

__all__ = [
    "DAMAGE_COLORS",
    "MAP_DAMAGE_TYPES",
    "SEVERITY_OPACITY",
    "CellChange",
    "CellCorrection",
    "CellRef",
    "CellSource",
    "ChangeKind",
    "DamageDetector",
    "DetectionInput",
    "DetectionOutput",
    "Grid",
    "MapCell",
    "MapScore",
    "MapStatus",
    "Quad",
    "TypeScore",
    "WallSize",
]

DEFAULT_LIST_LIMIT = 100


class DetectorStatus(StrEnum):
    OK = "ok"
    FAILED = "failed"
    MANUAL = "manual"


@dataclass(frozen=True)
class WallSpec:
    name: str
    size: WallSize
    site_id: UUID | None = None
    facade_id: UUID | None = None


@dataclass(frozen=True)
class PreparedWall:
    photo_jpeg: bytes
    quad: Quad
    grid: Grid
    rectified: RectifiedWall

    def detection_input(self) -> DetectionInput:
        return DetectionInput(
            rectified_jpeg=self.rectified.jpeg,
            labeled_jpeg=self.rectified.labeled_jpeg,
            width_px=self.rectified.width_px,
            height_px=self.rectified.height_px,
            grid=self.grid,
        )


@dataclass(frozen=True)
class DetectionRun:
    detector: str
    status: DetectorStatus
    output: DetectionOutput


@dataclass(frozen=True)
class MapView:
    id: UUID
    site_id: UUID | None
    facade_id: UUID | None
    wall_name: str
    wall: WallSize
    grid: Grid
    corners: list[list[float]]
    photo_key: str
    rectified_key: str
    rectified_width_px: int
    rectified_height_px: int
    detector: str
    detector_status: DetectorStatus
    summary_ar: str
    status: MapStatus
    cells: tuple[MapCell, ...]
    model_cells: tuple[MapCell, ...]
    created_at: datetime
    approved_at: datetime | None

    @property
    def damaged_area_m2(self) -> float:
        return len(self.cells) * self.grid.cell_area_m2(self.wall)


@dataclass(frozen=True)
class MapSummary:
    id: UUID
    site_id: UUID | None
    facade_id: UUID | None
    wall_name: str
    status: MapStatus
    detector_status: DetectorStatus
    damaged_cells: int
    urgent_cells: int
    total_cells: int
    rectified_key: str
    created_at: datetime


class PhotoUnusable(SaduError):
    status = 422

    def __init__(self, reason: RetakeReason | None) -> None:
        key = f"retake.{reason or 'unusable_wall'}"
        super().__init__("photo_unusable", reason_ar=translate(key, "ar"), reason_en=translate(key, "en"))
        self.reason = reason


def build_detector(settings: Settings, llm: LLMPort) -> DamageDetector:
    kind = settings.sadu_damage_detector
    if kind is DetectorKind.CLAUDE:
        return ClaudeGridDetector(llm)
    if kind is DetectorKind.NONE:
        return ManualOnly()
    if not settings.sadu_detector_url:
        raise ValueError(f"SADU_DETECTOR_URL is required when SADU_DAMAGE_DETECTOR={kind}")
    token = settings.sadu_detector_token.get_secret_value() if settings.sadu_detector_token else None
    client = HttpModelClient(settings.sadu_detector_url, token, settings.sadu_detector_timeout_s)
    labels = LabelMap(json.loads(settings.sadu_detector_labels or "{}"))
    if kind is DetectorKind.HTTP_DETECTION:
        return HttpDetectionModel(client, labels, settings.sadu_detector_min_score)
    return HttpCellClassifier(client, labels, settings.sadu_detector_min_score)


def prepare_wall(photo_jpeg: bytes, quad: Quad, wall: WallSize, rows: int) -> PreparedWall:
    grid = Grid.for_wall(wall, rows)
    return PreparedWall(photo_jpeg, quad, grid, rectify_wall(photo_jpeg, quad, wall.aspect, grid))


async def detect_damage(detector: DamageDetector, prepared: PreparedWall) -> DetectionRun:
    try:
        output = await detector.detect(prepared.detection_input())
    except DetectorUnavailable:
        return DetectionRun(detector.name, DetectorStatus.FAILED, DetectionOutput(cells=()))
    if not output.usable:
        raise PhotoUnusable(output.retake_reason)
    status = DetectorStatus.MANUAL if isinstance(detector, ManualOnly) else DetectorStatus.OK
    return DetectionRun(detector.name, status, output)


async def save_map(
    session: AsyncSession,
    store: ObjectStore,
    *,
    wall: WallSpec,
    prepared: PreparedWall,
    run: DetectionRun,
    created_by: UUID | None,
) -> MapView:
    photo_key = new_object_key("maps/photos", "jpg")
    rectified_key = new_object_key("maps/rectified", "jpg")
    await store.put(photo_key, prepared.photo_jpeg, "image/jpeg")
    await store.put(rectified_key, prepared.rectified.jpeg, "image/jpeg")
    row = DamageMapRow(
        site_id=wall.site_id,
        facade_id=wall.facade_id,
        wall_name=wall.name,
        width_m=wall.size.width_m,
        height_m=wall.size.height_m,
        rows=prepared.grid.rows,
        cols=prepared.grid.cols,
        corners=prepared.quad.as_list(),
        photo_key=photo_key,
        rectified_key=rectified_key,
        rectified_width_px=prepared.rectified.width_px,
        rectified_height_px=prepared.rectified.height_px,
        detector=run.detector,
        detector_status=run.status,
        summary_ar=run.output.summary_ar,
        model_cells=[_cell_json(c) for c in run.output.cells],
        status=MapStatus.DRAFT,
        created_by=created_by,
    )
    session.add(row)
    await session.flush()
    _add_cell_rows(session, row.id, run.output.cells)
    await session.flush()
    return _view(row, run.output.cells)


async def get_map(session: AsyncSession, map_id: UUID) -> MapView:
    row = await session.get(DamageMapRow, map_id)
    if row is None:
        raise NotFound("not_found")
    return _view(row, await _cells(session, map_id))


async def list_maps(
    session: AsyncSession, *, site_id: UUID | None = None, facade_id: UUID | None = None
) -> list[MapSummary]:
    damaged = (
        select(
            DamageMapCellRow.map_id,
            func.count().label("damaged"),
            func.count().filter(DamageMapCellRow.severity == Severity.URGENT).label("urgent"),
        )
        .group_by(DamageMapCellRow.map_id)
        .subquery()
    )
    query = (
        select(DamageMapRow, func.coalesce(damaged.c.damaged, 0), func.coalesce(damaged.c.urgent, 0))
        .outerjoin(damaged, damaged.c.map_id == DamageMapRow.id)
        .order_by(DamageMapRow.created_at.desc())
        .limit(DEFAULT_LIST_LIMIT)
    )
    if site_id is not None:
        query = query.where(DamageMapRow.site_id == site_id)
    if facade_id is not None:
        query = query.where(DamageMapRow.facade_id == facade_id)
    return [
        MapSummary(
            id=row.id,
            site_id=row.site_id,
            facade_id=row.facade_id,
            wall_name=row.wall_name,
            status=MapStatus(row.status),
            detector_status=DetectorStatus(row.detector_status),
            damaged_cells=int(count),
            urgent_cells=int(urgent),
            total_cells=row.rows * row.cols,
            rectified_key=row.rectified_key,
            created_at=row.created_at,
        )
        for row, count, urgent in (await session.execute(query)).all()
    ]


async def correct_cells(
    session: AsyncSession, map_id: UUID, corrections: Iterable[CellCorrection]
) -> MapView:
    row = await _draft_row(session, map_id)
    grid = Grid(row.rows, row.cols)
    try:
        cells = apply_corrections(await _cells(session, map_id), corrections, grid)
    except ValueError as error:
        raise SaduError("validation_failed", status=422) from error
    await session.execute(delete(DamageMapCellRow).where(DamageMapCellRow.map_id == map_id))
    _add_cell_rows(session, map_id, cells)
    await session.flush()
    return _view(row, cells)


async def approve_map(session: AsyncSession, map_id: UUID, reviewer_id: UUID) -> MapView:
    row = await _draft_row(session, map_id)
    row.status = MapStatus.APPROVED
    row.approved_by = reviewer_id
    row.approved_at = datetime.now(UTC)
    await session.flush()
    return _view(row, await _cells(session, map_id))


async def previous_approved(session: AsyncSession, view: MapView) -> MapView | None:
    query = select(DamageMapRow).where(
        DamageMapRow.status == MapStatus.APPROVED,
        DamageMapRow.created_at < view.created_at,
        DamageMapRow.id != view.id,
    )
    if view.facade_id is not None:
        query = query.where(DamageMapRow.facade_id == view.facade_id)
    else:
        query = query.where(DamageMapRow.facade_id.is_(None), DamageMapRow.wall_name == view.wall_name)
        if view.site_id is not None:
            query = query.where(DamageMapRow.site_id == view.site_id)
    row = await session.scalar(query.order_by(DamageMapRow.created_at.desc()).limit(1))
    if row is None:
        return None
    return _view(row, await _cells(session, row.id))


async def damage_overlay(store: ObjectStore, view: MapView) -> bytes:
    rectified = await store.get(view.rectified_key)
    return await asyncio.to_thread(paint_damage, rectified, view.grid, view.cells)


def changes_between(before: MapView, after: MapView) -> list[CellChange] | None:
    if before.grid != after.grid:
        return None
    return compare_maps(before.cells, after.cells)


def treatment_plan(view: MapView, catalog: treatments.Catalog) -> treatments.TreatmentPlan:
    areas = [
        treatments.DamagedArea(t.damage_type, t.severity, t.area_m2, t.cells)
        for t in tally_areas(view.cells, view.grid, view.wall)
    ]
    return treatments.plan_treatments(areas, catalog)


async def accuracy(session: AsyncSession, site_id: UUID | None = None) -> MapScore:
    query = select(DamageMapRow).where(
        DamageMapRow.status == MapStatus.APPROVED, DamageMapRow.detector_status == DetectorStatus.OK
    )
    if site_id is not None:
        query = query.where(DamageMapRow.site_id == site_id)
    pairs = []
    for row in await session.scalars(query):
        expected = {c.ref: c.damage_type for c in await _cells(session, row.id)}
        predicted = {c.ref: c.damage_type for c in _cells_from_json(row.model_cells)}
        pairs.append(ScoredPair(row.rows * row.cols, predicted, expected))
    return score_maps(pairs)


async def _draft_row(session: AsyncSession, map_id: UUID) -> DamageMapRow:
    row = await session.get(DamageMapRow, map_id, with_for_update=True)
    if row is None:
        raise NotFound("not_found")
    if row.status != MapStatus.DRAFT:
        raise Conflict("map_already_approved")
    return row


async def _cells(session: AsyncSession, map_id: UUID) -> tuple[MapCell, ...]:
    rows = await session.scalars(
        select(DamageMapCellRow)
        .where(DamageMapCellRow.map_id == map_id)
        .order_by(DamageMapCellRow.row, DamageMapCellRow.col)
    )
    return tuple(
        MapCell(
            CellRef(r.row, r.col),
            DamageType(r.damage_type),
            Severity(r.severity),
            ModelConfidence(r.confidence),
            CellSource(r.source),
        )
        for r in rows
    )


def _add_cell_rows(session: AsyncSession, map_id: UUID, cells: Iterable[MapCell]) -> None:
    session.add_all(
        DamageMapCellRow(
            map_id=map_id,
            row=cell.ref.row,
            col=cell.ref.col,
            damage_type=cell.damage_type,
            severity=cell.severity,
            confidence=cell.confidence,
            source=cell.source,
        )
        for cell in cells
    )


def _cell_json(cell: MapCell) -> dict[str, Any]:
    return {
        "row": cell.ref.row,
        "col": cell.ref.col,
        "damage_type": cell.damage_type,
        "severity": cell.severity,
        "confidence": cell.confidence,
    }


def _cells_from_json(items: list[dict[str, Any]]) -> tuple[MapCell, ...]:
    return tuple(
        MapCell(
            CellRef(item["row"], item["col"]),
            DamageType(item["damage_type"]),
            Severity(item["severity"]),
            ModelConfidence(item["confidence"]),
            CellSource.MODEL,
        )
        for item in items
    )


def _view(row: DamageMapRow, cells: tuple[MapCell, ...]) -> MapView:
    return MapView(
        id=row.id,
        site_id=row.site_id,
        facade_id=row.facade_id,
        wall_name=row.wall_name,
        wall=WallSize(row.width_m, row.height_m),
        grid=Grid(row.rows, row.cols),
        corners=row.corners,
        photo_key=row.photo_key,
        rectified_key=row.rectified_key,
        rectified_width_px=row.rectified_width_px,
        rectified_height_px=row.rectified_height_px,
        detector=row.detector,
        detector_status=DetectorStatus(row.detector_status),
        summary_ar=row.summary_ar,
        status=MapStatus(row.status),
        cells=cells,
        model_cells=_cells_from_json(row.model_cells),
        created_at=row.created_at,
        approved_at=row.approved_at,
    )
