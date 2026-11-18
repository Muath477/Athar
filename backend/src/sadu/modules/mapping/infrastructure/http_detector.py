import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

from sadu.modules.mapping.application.ports import DetectionInput, DetectionOutput, DetectorUnavailable
from sadu.modules.mapping.domain.detections import (
    CellPrediction,
    Detection,
    cells_from_detections,
    cells_from_predictions,
)
from sadu.modules.mapping.domain.grid import Box, Grid
from sadu.modules.mapping.infrastructure.imaging import crop_cells
from sadu.shared.resilience import call_with_policy
from sadu.shared.vocabulary import DamageType, Severity

MAX_PARALLEL_CELL_REQUESTS = 8


class LabelMap:
    def __init__(self, overrides: Mapping[str, str]) -> None:
        self._overrides = {k.strip().lower(): DamageType(v) for k, v in overrides.items()}

    def damage_type(self, label: str) -> DamageType | None:
        key = label.strip().lower()
        if key in self._overrides:
            return self._overrides[key]
        try:
            return DamageType(key)
        except ValueError:
            return None


class HttpModelClient:
    def __init__(
        self,
        url: str,
        token: str | None,
        timeout_s: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = url
        self._headers = {"Content-Type": "image/jpeg", "Accept": "application/json"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"
        self._timeout_s = timeout_s
        self._transport = transport

    def session(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transport)

    async def post_image(self, client: httpx.AsyncClient, jpeg: bytes) -> Any:
        async def send() -> Any:
            response = await client.post(self._url, content=jpeg, headers=self._headers)
            response.raise_for_status()
            return response.json()

        try:
            return await call_with_policy("damage_model", send, timeout_s=self._timeout_s, retries=1)
        except (httpx.HTTPError, TimeoutError, ValueError) as error:
            raise DetectorUnavailable(f"damage model call failed: {type(error).__name__}") from error


class HttpDetectionModel:
    def __init__(self, client: HttpModelClient, labels: LabelMap, min_score: float) -> None:
        self._client = client
        self._labels = labels
        self._min_score = min_score

    @property
    def name(self) -> str:
        return "http_detection"

    async def detect(self, request: DetectionInput) -> DetectionOutput:
        async with self._client.session() as http:
            payload = await self._client.post_image(http, request.rectified_jpeg)
        detections = parse_detections(payload, self._labels, request.width_px, request.height_px)
        return DetectionOutput(cells_from_detections(detections, request.grid, min_score=self._min_score))


class HttpCellClassifier:
    def __init__(self, client: HttpModelClient, labels: LabelMap, min_score: float) -> None:
        self._client = client
        self._labels = labels
        self._min_score = min_score

    @property
    def name(self) -> str:
        return "http_cell_classification"

    async def detect(self, request: DetectionInput) -> DetectionOutput:
        crops = crop_cells(request.rectified_jpeg, request.grid)
        limit = asyncio.Semaphore(MAX_PARALLEL_CELL_REQUESTS)

        async def classify(http: httpx.AsyncClient, label: str, jpeg: bytes) -> list[CellPrediction]:
            async with limit:
                payload = await self._client.post_image(http, jpeg)
            return parse_cell_classes(payload, self._labels, request.grid, label)

        async with self._client.session() as http:
            results = await asyncio.gather(*(classify(http, label, jpeg) for label, jpeg in crops.items()))
        predictions = [p for cell in results for p in cell]
        return DetectionOutput(cells_from_predictions(predictions, min_score=self._min_score))


def parse_detections(payload: Any, labels: LabelMap, width_px: int, height_px: int) -> list[Detection]:
    if isinstance(payload, dict):
        return [d for item in payload.get("detections", []) if (d := _canonical(item, labels)) is not None]
    if isinstance(payload, list):
        return [d for item in payload if (d := _pixel_box(item, labels, width_px, height_px)) is not None]
    raise DetectorUnavailable("damage model returned an unexpected payload")


def parse_cell_classes(payload: Any, labels: LabelMap, grid: Grid, cell_label: str) -> list[CellPrediction]:
    if not isinstance(payload, list):
        raise DetectorUnavailable("damage model returned an unexpected payload")
    ref = grid.parse(cell_label)
    predictions = []
    for item in payload:
        damage_type = labels.damage_type(str(item.get("label", "")))
        if damage_type is not None and damage_type is not DamageType.NONE:
            predictions.append(CellPrediction(ref, damage_type, float(item.get("score", 0.0))))
    return predictions


def _canonical(item: dict[str, Any], labels: LabelMap) -> Detection | None:
    damage_type = labels.damage_type(str(item.get("label", "")))
    box_values = item.get("box")
    if damage_type is None or not isinstance(box_values, list) or len(box_values) != 4:
        return None
    box = Box.clipped(*(float(v) for v in box_values))
    if box is None:
        return None
    return Detection(damage_type, float(item.get("score", 0.0)), box, _severity(item.get("severity")))


def _pixel_box(item: dict[str, Any], labels: LabelMap, width_px: int, height_px: int) -> Detection | None:
    damage_type = labels.damage_type(str(item.get("label", "")))
    box_values = item.get("box")
    if damage_type is None or not isinstance(box_values, dict):
        return None
    try:
        x0, y0, x1, y1 = (float(box_values[k]) for k in ("xmin", "ymin", "xmax", "ymax"))
    except (KeyError, TypeError, ValueError):
        return None
    box = Box.clipped(x0 / width_px, y0 / height_px, x1 / width_px, y1 / height_px)
    if box is None:
        return None
    return Detection(damage_type, float(item.get("score", 0.0)), box)


def _severity(value: Any) -> Severity | None:
    try:
        return Severity(value)
    except ValueError:
        return None
