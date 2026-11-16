"""Synthetic mud-brick walls for CV tests, so tests need no real site photos."""

import cv2
import numpy as np
from numpy.typing import NDArray

type Image = NDArray[np.uint8]

WALL_SIZE = (640, 960)  # height, width


def mud_wall(seed: int = 7) -> Image:
    rng = np.random.default_rng(seed)
    height, width = WALL_SIZE
    base = np.zeros((height, width, 3), dtype=np.float32)
    base[:] = (95, 140, 180)  # BGR sandy brown
    base += rng.normal(0, 12, (height, width, 1))
    for _ in range(400):
        center = (int(rng.integers(0, width)), int(rng.integers(0, height)))
        radius = int(rng.integers(3, 14))
        shade = float(rng.uniform(-45, 35))
        cv2.circle(base, center, radius, (shade + 95, shade + 140, shade + 180), -1)
    for row in range(0, height, 48):
        cv2.line(base, (0, row), (width, row), (70, 105, 140), 2)
    return np.clip(base, 0, 255).astype(np.uint8)


def photograph(wall: Image, *, tilt_px: int = 40, brightness: float = 1.0) -> Image:
    """A visitor's view of the wall: perspective tilt and different exposure."""
    height, width = wall.shape[:2]
    source = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    target = np.float32(
        [
            [tilt_px, tilt_px // 2],
            [width - tilt_px // 3, 0],
            [width, height],
            [tilt_px // 2, height - tilt_px // 3],
        ]
    )
    view = cv2.warpPerspective(
        wall, cv2.getPerspectiveTransform(source, target), (width, height), borderMode=cv2.BORDER_REFLECT
    )
    return np.clip(view.astype(np.float32) * brightness, 0, 255).astype(np.uint8)


def with_crack(wall: Image) -> Image:
    cracked = wall.copy()
    points = np.array([[420, 120], [440, 200], [430, 260], [455, 340], [450, 420]], dtype=np.int32)
    cv2.polylines(cracked, [points], isClosed=False, color=(25, 35, 45), thickness=5)
    return cracked


def with_soft_shadow(wall: Image) -> Image:
    shadow = np.ones(wall.shape[:2], dtype=np.float32)
    cv2.ellipse(shadow, (300, 300), (160, 120), 0, 0, 360, 0.55, -1)
    shadow = cv2.GaussianBlur(shadow, (0, 0), 25)
    return np.clip(wall.astype(np.float32) * shadow[..., None], 0, 255).astype(np.uint8)


def unrelated_scene(seed: int = 99) -> Image:
    return mud_wall(seed=seed)[::-1, ::-1].copy()
