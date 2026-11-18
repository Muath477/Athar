import cv2
import numpy as np

from sadu.modules.mapping.domain.grid import Grid
from sadu.modules.mapping.domain.quad import Quad
from sadu.modules.mapping.infrastructure.imaging import crop_cells, rectify_wall


def photo_with_wall(corners_px: list[tuple[int, int]], size=(800, 600)) -> bytes:
    width, height = size
    image = np.zeros((height, width, 3), np.uint8)
    cv2.fillConvexPoly(image, np.array(corners_px, np.int32), (255, 255, 255))
    return cv2.imencode(".jpg", image)[1].tobytes()


def decode(jpeg: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)


def test_rectified_wall_fills_the_frame_at_the_wall_aspect():
    corners = [(160, 90), (680, 60), (720, 540), (120, 510)]
    quad = Quad.from_list([[x / 799, y / 599] for x, y in corners])
    wall = rectify_wall(photo_with_wall(corners), quad, wall_aspect=2.0, grid=Grid(4, 8))

    assert (wall.width_px, wall.height_px) == (1200, 600)
    rectified = decode(wall.jpeg)
    inner = rectified[20:-20, 20:-20]
    assert inner.mean() > 240


def test_tall_walls_keep_their_long_side_vertical():
    wall = rectify_wall(
        photo_with_wall([(0, 0), (799, 0), (799, 599), (0, 599)]), Quad.full_frame(), 0.5, Grid(8, 4)
    )
    assert (wall.width_px, wall.height_px) == (600, 1200)


def test_labelled_image_draws_the_grid_over_the_wall():
    wall = rectify_wall(
        photo_with_wall([(0, 0), (799, 0), (799, 599), (0, 599)]), Quad.full_frame(), 2.0, Grid(4, 8)
    )
    assert not np.array_equal(decode(wall.labeled_jpeg), decode(wall.jpeg))


def test_cells_are_cropped_one_per_label():
    wall = rectify_wall(
        photo_with_wall([(0, 0), (799, 0), (799, 599), (0, 599)]), Quad.full_frame(), 2.0, Grid(2, 4)
    )
    crops = crop_cells(wall.jpeg, Grid(2, 4))
    assert sorted(crops) == ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"]
    assert decode(crops["B4"]).shape[:2] == (300, 300)
