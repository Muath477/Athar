import json

import cv2
import httpx
import numpy as np
import pytest

from sadu.modules.mapping.api import build_detector
from sadu.modules.mapping.application.element_prompt import (
    PROMPT_VERSION,
    InvalidAnswer,
    elements_answer,
    parse_elements,
)
from sadu.modules.mapping.application.ports import DetectionInput, DetectorUnavailable, ModelChoice
from sadu.modules.mapping.domain.grid import Grid
from sadu.modules.mapping.infrastructure.qwen_detector import QwenEndpoint, QwenVisionDetector, parse_answer
from sadu.shared.config import DetectorKind, Settings
from sadu.shared.vocabulary import DamageType, ModelConfidence, Severity
from tests.fakes import FakeLLM

GRID = Grid(2, 4)
BEARER = "local-key"
CRACK = {
    "damage_type": "crack",
    "geometry": "line",
    "points": [[0.05, 0.2], [0.2, 0.3]],
    "severity": "moderate",
    "damage_class": "from_1_to_5mm",
    "confidence": "high",
}
CAVITY = {
    "damage_type": "cavity",
    "geometry": "point",
    "points": [[0.9, 0.9]],
    "severity": "watch",
    "damage_class": "small",
    "confidence": "low",
}


def detection_input() -> DetectionInput:
    jpeg = cv2.imencode(".jpg", np.full((200, 400, 3), 180, np.uint8))[1].tobytes()
    return DetectionInput(jpeg, jpeg, 400, 200, GRID)


class FakeServer:
    def __init__(self, *answers: str | Exception, status: int = 200) -> None:
        self.answers = list(answers)
        self.status = status
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.reply)

    def reply(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        body = {"choices": [{"message": {"role": "assistant", "content": answer}}]}
        return httpx.Response(self.status, json=body)

    def body(self, index: int) -> dict:
        return json.loads(self.requests[index].content)


def detector(server: FakeServer, active: ModelChoice | None = None) -> QwenVisionDetector:
    async def lookup() -> ModelChoice | None:
        return active

    endpoint = QwenEndpoint("http://localhost:8080/v1", "athar-damage", timeout_s=5.0, token=BEARER)
    return QwenVisionDetector(endpoint, lookup, server.transport())


@pytest.mark.anyio
async def test_qwen_answer_becomes_elements_cells_and_a_recorded_model():
    server = FakeServer("```json\n" + json.dumps({"elements": [CRACK, CAVITY]}) + "\n```")
    output = await detector(server, ModelChoice("athar-damage-v2", "2")).detect(detection_input())

    assert [(e.id, e.damage_type, e.damage_class) for e in output.elements] == [
        ("E1", DamageType.CRACK, "from_1_to_5mm"),
        ("E2", DamageType.CAVITY, "small"),
    ]
    assert [(c.ref.label, c.damage_type, c.severity) for c in output.cells] == [
        ("A1", DamageType.CRACK, Severity.MODERATE),
        ("B4", DamageType.CAVITY, Severity.WATCH),
    ]
    assert output.elements[1].confidence is ModelConfidence.LOW
    assert (output.model, output.prompt_version) == ("athar-damage-v2@2", PROMPT_VERSION)

    sent = server.requests[0]
    assert str(sent.url) == "http://localhost:8080/v1/chat/completions"
    assert sent.headers["Authorization"] == f"Bearer {BEARER}"
    body = server.body(0)
    assert body["model"] == "athar-damage-v2"
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert body["response_format"]["type"] == "json_schema"
    image = body["messages"][1]["content"][0]["image_url"]["url"]
    assert image.startswith("data:image/jpeg;base64,")


@pytest.mark.anyio
async def test_unregistered_model_falls_back_to_the_configured_name():
    server = FakeServer(json.dumps({"elements": []}))
    output = await detector(server).detect(detection_input())
    assert server.body(0)["model"] == "athar-damage"
    assert output.model == "athar-damage@unregistered"
    assert output.cells == () and output.elements == ()


@pytest.mark.anyio
async def test_an_invalid_answer_gets_one_repair_request():
    server = FakeServer('{"elements": [{"damage_type": "crack"', json.dumps({"elements": [CRACK]}))
    output = await detector(server).detect(detection_input())
    assert len(output.elements) == 1
    repair = server.body(1)["messages"]
    assert repair[-2]["role"] == "assistant"
    assert "not valid JSON" in repair[-1]["content"]


@pytest.mark.anyio
async def test_a_second_invalid_answer_sends_the_map_to_manual_work():
    wrong_geometry = {**CRACK, "geometry": "area"}
    server = FakeServer("no json here", json.dumps({"elements": [wrong_geometry]}))
    with pytest.raises(DetectorUnavailable, match="invalid after a repair"):
        await detector(server).detect(detection_input())
    assert len(server.requests) == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("server", "reason"),
    [
        (FakeServer(httpx.ReadTimeout("slow")), "ReadTimeout"),
        (FakeServer("{}", status=503), "HTTPStatusError"),
    ],
)
async def test_outages_and_timeouts_are_reported_as_unavailable(server, reason):
    with pytest.raises(DetectorUnavailable, match=reason):
        await detector(server).detect(detection_input())


@pytest.mark.parametrize(
    ("answer", "problem"),
    [
        ([], "must be an object"),
        ({"elements": [{**CRACK, "damage_class": "deep"}]}, "not a class of crack"),
        ({"elements": [{**CAVITY, "damage_type": "moisture", "geometry": "area"}]}, "not one of the mapped"),
        ({"elements": [{**CRACK, "points": [[0.1, 1.4], [0.2, 0.2]]}]}, "must lie on the wall"),
        ({"elements": [{**CRACK, "severity": "severe"}]}, "missing or unknown field"),
    ],
)
def test_strict_parsing_names_the_problem(answer, problem):
    with pytest.raises(InvalidAnswer, match=problem):
        parse_elements(answer)


def test_thinking_blocks_are_ignored_and_answers_round_trip():
    elements = parse_answer("<think>looking</think>" + json.dumps({"elements": [CRACK, CAVITY]}))
    assert elements_answer(elements) == {"elements": [CRACK, CAVITY]}


def test_settings_select_the_qwen_detector():
    settings = Settings(sadu_damage_detector=DetectorKind.QWEN)
    built = build_detector(settings, FakeLLM())
    assert built.name == "qwen"
    assert settings.sadu_qwen_url == "http://localhost:8080/v1"
    assert settings.sadu_qwen_timeout_s == 120.0
