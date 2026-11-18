import json
from pathlib import Path

import pytest

CRACK = {
    "id": "E1",
    "damage_type": "crack",
    "points": [[0.1, 0.1], [0.1, 0.4]],
    "severity": "moderate",
    "confidence": "high",
    "source": "expert",
    "damage_class": "from_1_to_5mm",
}
LOSS = {
    "id": "E2",
    "damage_type": "plaster_loss",
    "points": [[0.5, 0.5], [1.0, 0.5], [1.0, 1.0], [0.5, 1.0]],
    "severity": "watch",
    "confidence": "medium",
    "source": "model",
    "damage_class": None,
}


def map_record(map_id: str, site: str | None, *, quality: str = "expert", detector: str = "grid_api") -> dict:
    return {
        "map_id": map_id,
        "site_id": site,
        "facade_id": None,
        "image": f"images/{map_id}.jpg",
        "width_m": 10.0,
        "height_m": 5.0,
        "rows": 4,
        "cols": 8,
        "elements": [CRACK, LOSS],
        "detector": detector,
        "detector_status": "ok",
        "detector_cells": [
            {"row": 0, "col": 0, "damage_type": "crack", "severity": "watch", "confidence": "high"}
        ],
        "label_quality": quality,
    }


@pytest.fixture
def athar_export(tmp_path: Path) -> Path:
    folder = tmp_path / "athar"
    folder.mkdir()
    records = [map_record(f"m{i}", f"site-{i % 5}") for i in range(20)]
    (folder / "manifest.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    return folder
