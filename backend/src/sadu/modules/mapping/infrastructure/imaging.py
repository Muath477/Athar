from dataclasses import dataclass

import cv2
import numpy as np

from sadu.modules.mapping.domain.damage_map import MapCell
from sadu.modules.mapping.domain.elements import Element
from sadu.modules.mapping.domain.glossary import Geometry
from sadu.modules.mapping.domain.grid import Grid
from sadu.modules.mapping.domain.palette import DAMAGE_COLORS, SEVERITY_OPACITY, bgr
from sadu.modules.mapping.domain.quad import Quad
from sadu.shared.errors import SaduError
from sadu.shared.vocabulary import DamageType

RECTIFIED_LONG_SIDE_PX = 1200
JPEG_QUALITY = 88
GRID_COLOR = (255, 255, 255)
LABEL_BACKGROUND = (0, 0, 0)
OUTLINE_BGR = (60, 60, 60)
LABEL_BGR = (0, 0, 0)
LABEL_TEXT_BGR = (255, 255, 255)


@dataclass(frozen=True)
class RectifiedWall:
    jpeg: bytes
    labeled_jpeg: bytes
    width_px: int
    height_px: int


def rectify_wall(photo_jpeg: bytes, quad: Quad, wall_aspect: float, grid: Grid) -> RectifiedWall:
    photo = cv2.imdecode(np.frombuffer(photo_jpeg, np.uint8), cv2.IMREAD_COLOR)
    if photo is None:
        raise SaduError("unsupported_image", status=415)
    height, width = photo.shape[:2]
    out_w, out_h = _output_size(wall_aspect)
    source = np.array([[x * (width - 1), y * (height - 1)] for x, y in quad.points], dtype=np.float32)
    target = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], dtype=np.float32)
    transform = cv2.getPerspectiveTransform(source, target)
    rectified = cv2.warpPerspective(photo, transform, (out_w, out_h), flags=cv2.INTER_LINEAR)
    labeled = draw_grid(rectified.copy(), grid)
    return RectifiedWall(_encode(rectified), _encode(labeled), out_w, out_h)


def draw_grid(image: np.ndarray, grid: Grid) -> np.ndarray:
    height, width = image.shape[:2]
    for col in range(1, grid.cols):
        x = round(col * width / grid.cols)
        cv2.line(image, (x, 0), (x, height - 1), GRID_COLOR, 1, cv2.LINE_AA)
    for row in range(1, grid.rows):
        y = round(row * height / grid.rows)
        cv2.line(image, (0, y), (width - 1, y), GRID_COLOR, 1, cv2.LINE_AA)
    font_scale = max(0.35, min(width / grid.cols, height / grid.rows) / 120)
    for ref in grid.cells():
        x = round(ref.col * width / grid.cols) + 3
        y = round(ref.row * height / grid.rows) + 3
        (text_w, text_h), baseline = cv2.getTextSize(ref.label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        cv2.rectangle(image, (x, y), (x + text_w + 4, y + text_h + baseline + 2), LABEL_BACKGROUND, -1)
        cv2.putText(
            image,
            ref.label,
            (x + 2, y + text_h + 1),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            GRID_COLOR,
            1,
            cv2.LINE_AA,
        )
    return image


def paint_damage(rectified_jpeg: bytes, grid: Grid, cells: tuple[MapCell, ...]) -> bytes:
    image = cv2.imdecode(np.frombuffer(rectified_jpeg, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise SaduError("unsupported_image", status=415)
    height, width = image.shape[:2]
    for cell in cells:
        x0, x1 = round(cell.ref.col * width / grid.cols), round((cell.ref.col + 1) * width / grid.cols)
        y0, y1 = round(cell.ref.row * height / grid.rows), round((cell.ref.row + 1) * height / grid.rows)
        tile = image[y0:y1, x0:x1]
        fill = np.full_like(tile, bgr(DAMAGE_COLORS[cell.damage_type]))
        opacity = SEVERITY_OPACITY[cell.severity]
        image[y0:y1, x0:x1] = cv2.addWeighted(fill, opacity, tile, 1 - opacity, 0)
    return _encode(draw_grid(image, grid))


def paint_elements(rectified_jpeg: bytes, grid: Grid, elements: tuple[Element, ...]) -> bytes:
    image = cv2.imdecode(np.frombuffer(rectified_jpeg, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise SaduError("unsupported_image", status=415)
    height, width = image.shape[:2]
    image = draw_grid(image, grid)
    stroke = max(2, round(min(width, height) / 160))
    for element in elements:
        colour = bgr(DAMAGE_COLORS[element.damage_type])
        outline = OUTLINE_BGR if element.damage_type is DamageType.SALT_EFFLORESCENCE else colour
        pixels = np.array([[round(x * width), round(y * height)] for x, y in element.points], np.int32)
        if element.geometry is Geometry.AREA:
            layer = image.copy()
            cv2.fillPoly(layer, [pixels], colour)
            image = cv2.addWeighted(
                layer, SEVERITY_OPACITY[element.severity], image, 1 - SEVERITY_OPACITY[element.severity], 0
            )
            cv2.polylines(
                image, [pixels], isClosed=True, color=outline, thickness=stroke, lineType=cv2.LINE_AA
            )
        elif element.geometry is Geometry.LINE:
            cv2.polylines(
                image, [pixels], isClosed=False, color=colour, thickness=stroke + 1, lineType=cv2.LINE_AA
            )
        else:
            cv2.circle(image, tuple(int(v) for v in pixels[0]), stroke * 3, colour, -1, cv2.LINE_AA)
            cv2.circle(image, tuple(int(v) for v in pixels[0]), stroke * 3, OUTLINE_BGR, 1, cv2.LINE_AA)
        x, y = pixels[0]
        cv2.putText(
            image,
            element.id,
            (int(x) + stroke * 2, int(y) - stroke * 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4 + stroke / 10,
            LABEL_BGR,
            stroke,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            element.id,
            (int(x) + stroke * 2, int(y) - stroke * 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4 + stroke / 10,
            LABEL_TEXT_BGR,
            max(1, stroke // 2),
            cv2.LINE_AA,
        )
    return _encode(image)


def crop_cells(rectified_jpeg: bytes, grid: Grid) -> dict[str, bytes]:
    image = cv2.imdecode(np.frombuffer(rectified_jpeg, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise SaduError("unsupported_image", status=415)
    height, width = image.shape[:2]
    crops = {}
    for ref in grid.cells():
        x0, x1 = round(ref.col * width / grid.cols), round((ref.col + 1) * width / grid.cols)
        y0, y1 = round(ref.row * height / grid.rows), round((ref.row + 1) * height / grid.rows)
        crops[ref.label] = _encode(image[y0:y1, x0:x1])
    return crops


def _output_size(wall_aspect: float) -> tuple[int, int]:
    if wall_aspect >= 1:
        return RECTIFIED_LONG_SIDE_PX, max(1, round(RECTIFIED_LONG_SIDE_PX / wall_aspect))
    return max(1, round(RECTIFIED_LONG_SIDE_PX * wall_aspect)), RECTIFIED_LONG_SIDE_PX


def _encode(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise SaduError("unsupported_image", status=415)
    return bytes(buffer.tobytes())
