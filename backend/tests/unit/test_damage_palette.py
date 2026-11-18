import re
from pathlib import Path

import cv2
import numpy as np

from sadu.modules.mapping.domain.damage_map import CellSource, MapCell
from sadu.modules.mapping.domain.grid import CellRef, Grid
from sadu.modules.mapping.domain.palette import DAMAGE_COLORS, SEVERITY_OPACITY, bgr
from sadu.modules.mapping.infrastructure.imaging import paint_damage
from sadu.shared.vocabulary import DamageType, ModelConfidence, Severity

FRONTEND_PALETTE = Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "damage-palette.ts"


def test_backend_palette_matches_the_dashboard():
    source = FRONTEND_PALETTE.read_text(encoding="utf-8")
    colors = dict(re.findall(r"(\w+): \"(#[0-9a-f]{6})\"", source))
    opacities = {k: float(v) for k, v in re.findall(r"(watch|moderate|urgent): ([0-9.]+)", source)}
    assert {str(k): v for k, v in DAMAGE_COLORS.items()} == {k: colors[k] for k in map(str, DAMAGE_COLORS)}
    assert {str(k): v for k, v in SEVERITY_OPACITY.items()} == opacities


def test_painting_tints_only_the_damaged_cell():
    grid = Grid(rows=2, cols=2)
    white = np.full((200, 200, 3), 255, np.uint8)
    jpeg = cv2.imencode(".jpg", white, [cv2.IMWRITE_JPEG_QUALITY, 95])[1].tobytes()
    urgent_crack = MapCell(
        CellRef(1, 1), DamageType.CRACK, Severity.URGENT, ModelConfidence.HIGH, CellSource.MODEL
    )

    painted = cv2.imdecode(
        np.frombuffer(paint_damage(jpeg, grid, (urgent_crack,)), np.uint8), cv2.IMREAD_COLOR
    )

    expected = 0.72 * np.array(bgr(DAMAGE_COLORS[DamageType.CRACK])) + 0.28 * 255
    assert np.allclose(painted[160, 160], expected, atol=12)
    assert np.allclose(painted[40, 160], [255, 255, 255], atol=12)
