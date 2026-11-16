"""Facade planes and pin placement (docs/03-architecture.md §10)."""

import math
from dataclasses import dataclass

type Vec3 = tuple[float, float, float]

PIN_OFFSET_M = 0.02


@dataclass(frozen=True)
class FacadePlane:
    origin: Vec3
    u_axis: Vec3
    v_axis: Vec3
    normal: Vec3
    width_m: float
    height_m: float

    @classmethod
    def from_corners(cls, corners: list[Vec3]) -> "FacadePlane":
        """Corners in order: bottom-left, bottom-right, top-right, top-left."""
        if len(corners) != 4:
            raise ValueError(f"A facade needs 4 corners, got {len(corners)}")
        bottom_left, bottom_right, _, top_left = corners
        along = _sub(bottom_right, bottom_left)
        up = _sub(top_left, bottom_left)
        width, height = _norm(along), _norm(up)
        if width == 0 or height == 0:
            raise ValueError("Facade corners must not coincide")
        u_axis, v_axis = _scale(along, 1 / width), _scale(up, 1 / height)
        normal = _cross(u_axis, v_axis)
        return cls(bottom_left, u_axis, v_axis, _scale(normal, 1 / _norm(normal)), width, height)

    def uv_to_xyz(self, u: float, v: float) -> Vec3:
        """Map facade UV (0..1 left to right, 0..1 bottom to top) to a point just off the wall."""
        u, v = _clamp01(u), _clamp01(v)
        point = _add(self.origin, _scale(self.u_axis, u * self.width_m))
        point = _add(point, _scale(self.v_axis, v * self.height_m))
        return _add(point, _scale(self.normal, PIN_OFFSET_M))


def heading_score(camera_heading_deg: float, outward_azimuth_deg: float) -> float:
    """1.0 when the camera faces the facade head-on, -1.0 when it faces away."""
    facing_direction = (outward_azimuth_deg + 180.0) % 360.0
    return math.cos(math.radians(camera_heading_deg - facing_direction))


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(a: Vec3, k: float) -> Vec3:
    return (a[0] * k, a[1] * k, a[2] * k)


def _norm(a: Vec3) -> float:
    return math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def image_point_to_uv(homography: list[list[float]], x: float, y: float) -> tuple[float, float]:
    """Apply a baseline-pixel -> facade-UV homography to one point."""
    h = homography
    w = h[2][0] * x + h[2][1] * y + h[2][2]
    if w == 0:
        raise ValueError("Point maps to infinity under this homography")
    u = (h[0][0] * x + h[0][1] * y + h[0][2]) / w
    v = (h[1][0] * x + h[1][1] * y + h[1][2]) / w
    return (_clamp01(u), _clamp01(v))
