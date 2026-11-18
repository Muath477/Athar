import json

import cv2
import httpx
import numpy as np
import pytest

from sadu.modules.mapping.application.claude_detector import ClaudeGridDetector, parse_response
from sadu.modules.mapping.application.ports import DetectionInput, DetectorUnavailable
from sadu.modules.mapping.domain.detections import Detection, cells_from_detections
from sadu.modules.mapping.domain.grid import Box, CellRef, Grid
from sadu.modules.mapping.infrastructure.http_detector import (
    HttpCellClassifier,
    HttpDetectionModel,
    HttpModelClient,
    LabelMap,
    parse_detections,
)
from sadu.shared.vocabulary import DamageType, ModelConfidence, RetakeReason, Severity
from tests.fakes import FakeLLM

GRID = Grid(2, 4)


def wall_jpeg(width=400, height=200) -> bytes:
    image = np.full((height, width, 3), 180, np.uint8)
    return cv2.imencode(".jpg", image)[1].tobytes()


def detection_input() -> DetectionInput:
    jpeg = wall_jpeg()
    return DetectionInput(jpeg, jpeg, 400, 200, GRID)


def test_claude_response_keeps_known_cells_only():
    output = parse_response(
        {
            "image_usable": True,
            "retake_reason": "none",
            "summary_ar": "تشقق في أعلى الجدار.",
            "cells": [
                {"cell": "A1", "damage_type": "crack", "severity": "moderate", "confidence": "high"},
                {"cell": "A1", "damage_type": "moisture", "severity": "watch", "confidence": "high"},
                {"cell": "C1", "damage_type": "crack", "severity": "watch", "confidence": "low"},
                {"cell": "B2", "damage_type": "new_construction", "severity": "watch", "confidence": "low"},
            ],
        },
        GRID,
    )
    assert [(c.ref.label, c.damage_type, c.severity) for c in output.cells] == [
        ("A1", DamageType.CRACK, Severity.MODERATE)
    ]
    assert output.usable


def test_claude_unusable_photo_carries_the_reason_and_no_cells():
    output = parse_response(
        {
            "image_usable": False,
            "retake_reason": "too_dark",
            "summary_ar": "",
            "cells": [{"cell": "A1", "damage_type": "crack", "severity": "watch", "confidence": "low"}],
        },
        GRID,
    )
    assert (output.usable, output.retake_reason, output.cells) == (False, RetakeReason.TOO_DARK, ())


@pytest.mark.anyio
async def test_claude_detector_sends_the_labelled_image_and_reports_outages():
    llm = FakeLLM(lambda _: {"image_usable": True, "retake_reason": "none", "summary_ar": "", "cells": []})
    request = detection_input()
    await ClaudeGridDetector(llm).detect(request)
    sent = llm.requests[0]
    assert sent.images[0].data == request.labeled_jpeg
    assert "2 rows" in sent.text and "4 columns" in sent.text

    with pytest.raises(DetectorUnavailable):
        await ClaudeGridDetector(FakeLLM()).detect(request)


def test_detections_mark_cells_they_cover_enough():
    detections = [
        Detection(DamageType.CRACK, 0.9, Box(0.0, 0.0, 0.3, 0.5)),
        Detection(DamageType.MOISTURE, 0.2, Box(0.5, 0.5, 1.0, 1.0)),
    ]
    cells = cells_from_detections(detections, GRID, min_score=0.35)
    assert [(c.ref.label, c.confidence) for c in cells] == [
        ("A1", ModelConfidence.HIGH),
        ("A2", ModelConfidence.HIGH),
    ]


def test_label_map_uses_overrides_then_damage_type_names():
    labels = LabelMap({"Spalling": "plaster_loss"})
    assert labels.damage_type("spalling") is DamageType.PLASTER_LOSS
    assert labels.damage_type("Crack") is DamageType.CRACK
    assert labels.damage_type("person") is None


def test_parse_detections_accepts_canonical_and_hugging_face_payloads():
    labels = LabelMap({})
    canonical = parse_detections(
        {"detections": [{"label": "crack", "score": 0.8, "box": [0.1, 0.1, 0.2, 0.2], "severity": "urgent"}]},
        labels,
        400,
        200,
    )
    assert canonical[0].severity is Severity.URGENT
    hugging_face = parse_detections(
        [{"label": "crack", "score": 0.7, "box": {"xmin": 0, "ymin": 0, "xmax": 200, "ymax": 100}}],
        labels,
        400,
        200,
    )
    assert hugging_face[0].box == Box(0.0, 0.0, 0.5, 0.5)
    with pytest.raises(DetectorUnavailable):
        parse_detections("oops", labels, 400, 200)


@pytest.mark.anyio
async def test_http_detection_model_posts_the_rectified_photo():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = [{"label": "crack", "score": 0.9, "box": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 100}}]
        return httpx.Response(200, json=body)

    client = HttpModelClient("https://model.test/detect", "secret", 5, httpx.MockTransport(handler))
    output = await HttpDetectionModel(client, LabelMap({}), 0.35).detect(detection_input())
    assert [c.ref for c in output.cells] == [CellRef(0, 0)]
    assert seen[0].headers["Authorization"] == "Bearer secret"
    assert seen[0].headers["Content-Type"] == "image/jpeg"


@pytest.mark.anyio
async def test_http_cell_classifier_asks_once_per_cell():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        label = "Positive" if len(calls) == 1 else "Negative"
        return httpx.Response(200, content=json.dumps([{"label": label, "score": 0.95}]))

    client = HttpModelClient("https://model.test/classify", None, 5, httpx.MockTransport(handler))
    labels = LabelMap({"Positive": "crack", "Negative": "none"})
    output = await HttpCellClassifier(client, labels, 0.5).detect(detection_input())
    assert len(calls) == GRID.rows * GRID.cols
    assert len(output.cells) == 1 and output.cells[0].damage_type is DamageType.CRACK


@pytest.mark.anyio
async def test_http_model_errors_become_detector_unavailable():
    client = HttpModelClient(
        "https://model.test", None, 5, httpx.MockTransport(lambda _: httpx.Response(503))
    )
    with pytest.raises(DetectorUnavailable):
        await HttpDetectionModel(client, LabelMap({}), 0.35).detect(detection_input())
