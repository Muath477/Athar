import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from sadu.modules.watch.domain.scene import Mask, Window

EARTH_RADIUS_M = 6371008.8


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


@dataclass(frozen=True)
class Zones:
    inside: Mask
    ring: Mask


def local_xy(points: list[LatLon], center: LatLon) -> npt.NDArray[np.float64]:
    shrink = math.cos(math.radians(center.lat))
    return np.array(
        [
            (
                math.radians(p.lon - center.lon) * EARTH_RADIUS_M * shrink,
                math.radians(p.lat - center.lat) * EARTH_RADIUS_M,
            )
            for p in points
        ],
        dtype=np.float64,
    )


def pixel_centres(window: Window) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    offsets = (np.arange(window.size_px) + 0.5) * window.pixel_m - window.half_extent_m
    x, y = np.meshgrid(offsets, offsets[::-1])
    return x, y


def zones(boundary: list[LatLon], center: LatLon, window: Window, buffer_m: float) -> Zones:
    polygon = local_xy(boundary, center)
    x, y = pixel_centres(window)
    inside = _contains(polygon, x, y)
    near = _distance_to_edges(polygon, x, y) <= buffer_m
    return Zones(inside=inside, ring=np.asarray(near & ~inside))


def _contains(
    polygon: npt.NDArray[np.float64], x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
) -> Mask:
    inside = np.zeros(x.shape, dtype=bool)
    count = len(polygon)
    for i in range(count):
        x0, y0 = polygon[i]
        x1, y1 = polygon[(i + 1) % count]
        if y0 == y1:
            continue
        crosses = (y0 > y) != (y1 > y)
        x_at_y = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
        inside ^= crosses & (x < x_at_y)
    return inside


def _distance_to_edges(
    polygon: npt.NDArray[np.float64], x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
) -> npt.NDArray[np.float64]:
    nearest = np.full(x.shape, np.inf)
    count = len(polygon)
    for i in range(count):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % count]
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        t = np.zeros_like(x) if length_sq == 0 else np.clip(((x - ax) * dx + (y - ay) * dy) / length_sq, 0, 1)
        nearest = np.minimum(nearest, np.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return nearest


def window_for(boundary: list[LatLon], center: LatLon, buffer_m: float, pixel_m: float = 10.0) -> Window:
    polygon = local_xy(boundary, center)
    reach = float(np.abs(polygon).max()) if len(polygon) else 0.0
    size = math.ceil(2 * (reach + buffer_m) / pixel_m) + 4
    return Window(size_px=min(max(size, 32), 256), pixel_m=pixel_m)
