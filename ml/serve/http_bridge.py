import argparse
import itertools
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ml.serve.client import DEFAULT_MODEL, DEFAULT_TIMEOUT_S, DEFAULT_URL, ChatEndpoint
from sadu.modules.mapping.application.element_prompt import (
    InvalidAnswer,
    parse_answer,
    repair_messages,
    wall_messages,
)
from sadu.modules.mapping.domain.elements import Element
from sadu.modules.mapping.domain.glossary import Geometry

CONFIDENCE_SCORE = {"high": 0.9, "medium": 0.6, "low": 0.4}
MIN_BOX_SIDE = 0.03
MAX_IMAGE_BYTES = 15 * 1024 * 1024


def detections(elements: tuple[Element, ...]) -> dict[str, list[dict[str, Any]]]:
    found = []
    for element in elements:
        for box in _boxes(element):
            found.append(
                {
                    "label": element.damage_type.value,
                    "score": CONFIDENCE_SCORE[element.confidence.value],
                    "box": [round(v, 4) for v in box],
                    "severity": element.severity.value,
                }
            )
    return {"detections": found}


def map_elements(endpoint: ChatEndpoint, jpeg: bytes) -> tuple[Element, ...]:
    messages = wall_messages(jpeg)
    answer = endpoint.complete(messages)
    try:
        return parse_answer(answer)
    except InvalidAnswer as error:
        return parse_answer(endpoint.complete(repair_messages(messages, answer, error)))


def _boxes(element: Element) -> list[tuple[float, float, float, float]]:
    if element.geometry is Geometry.LINE:
        return [_box([a, b]) for a, b in itertools.pairwise(element.points)]
    return [_box(list(element.points))]


def _box(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    x0, x1 = _span(min(xs), max(xs))
    y0, y1 = _span(min(ys), max(ys))
    return x0, y0, x1, y1


def _span(low: float, high: float) -> tuple[float, float]:
    pad = max(0.0, (MIN_BOX_SIDE - (high - low)) / 2)
    return max(0.0, low - pad), min(1.0, high + pad)


def handler_for(endpoint: ChatEndpoint) -> type[BaseHTTPRequestHandler]:
    class DetectHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_IMAGE_BYTES:
                self._reply(413, {"error": "send one JPEG of at most 15 MB"})
                return
            try:
                elements = map_elements(endpoint, self.rfile.read(length))
            except (InvalidAnswer, OSError, KeyError, ValueError) as error:
                self._reply(502, {"error": f"damage model failed: {type(error).__name__}"})
                return
            self._reply(200, detections(elements))

        def _reply(self, status: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return DetectHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the http_detection contract in front of the model")
    parser.add_argument("--upstream", default=os.environ.get("SADU_QWEN_URL", DEFAULT_URL))
    parser.add_argument("--model", default=os.environ.get("SADU_QWEN_MODEL", DEFAULT_MODEL))
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    endpoint = ChatEndpoint(args.upstream, args.model, args.timeout, os.environ.get("SADU_QWEN_TOKEN"))
    server = ThreadingHTTPServer((args.host, args.port), handler_for(endpoint))
    print(f"Detections on http://{args.host}:{args.port}/ from {args.upstream} ({args.model})")
    server.serve_forever()


if __name__ == "__main__":
    main()
