import math
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

EARTH_RADIUS_M = 6_371_008.8
SITE_MATCH_RADIUS_M = 60

type PlanePoint = tuple[float, float]


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float


@dataclass(frozen=True)
class PhotoMetadata:
    location: GeoPoint | None = None
    taken_at: datetime | None = None


@dataclass(frozen=True)
class FacadeFootprint:
    facade_id: UUID
    start: PlanePoint
    end: PlanePoint
    outward_azimuth_deg: float

    @classmethod
    def from_site_corners(
        cls, facade_id: UUID, corners: list[list[float]], outward_azimuth_deg: float
    ) -> "FacadeFootprint":
        bottom_left, bottom_right = corners[0], corners[1]
        return cls(
            facade_id,
            _ground_point(bottom_left),
            _ground_point(bottom_right),
            outward_azimuth_deg,
        )

    def distance_m(self, point: PlanePoint) -> float:
        dx, dy = self.end[0] - self.start[0], self.end[1] - self.start[1]
        length_sq = dx * dx + dy * dy
        t = 0.0
        if length_sq > 0:
            t = ((point[0] - self.start[0]) * dx + (point[1] - self.start[1]) * dy) / length_sq
            t = min(1.0, max(0.0, t))
        nearest = (self.start[0] + t * dx, self.start[1] + t * dy)
        return math.dist(point, nearest)

    def faces(self, point: PlanePoint) -> bool:
        middle = ((self.start[0] + self.end[0]) / 2, (self.start[1] + self.end[1]) / 2)
        azimuth = math.radians(self.outward_azimuth_deg)
        outward = (math.sin(azimuth), math.cos(azimuth))
        return (point[0] - middle[0]) * outward[0] + (point[1] - middle[1]) * outward[1] > 0


def distance_m(a: GeoPoint, b: GeoPoint) -> float:
    lat_a, lat_b = math.radians(a.lat), math.radians(b.lat)
    d_lat = lat_b - lat_a
    d_lon = math.radians(b.lon - a.lon)
    h = math.sin(d_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def east_north_offset_m(origin: GeoPoint, point: GeoPoint) -> PlanePoint:
    east = math.radians(point.lon - origin.lon) * EARTH_RADIUS_M * math.cos(math.radians(origin.lat))
    north = math.radians(point.lat - origin.lat) * EARTH_RADIUS_M
    return (east, north)


def nearest_facade(origin: GeoPoint, photo: GeoPoint, facades: list[FacadeFootprint]) -> UUID | None:
    if not facades:
        return None
    position = east_north_offset_m(origin, photo)
    facing = [f for f in facades if f.faces(position)]
    candidates = facing or facades
    return min(candidates, key=lambda f: f.distance_m(position)).facade_id


def _ground_point(corner: list[float]) -> PlanePoint:
    x, _, z = corner
    return (x, -z)
