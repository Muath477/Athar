from dataclasses import dataclass

type Point = tuple[float, float]

MIN_AREA_FRACTION = 0.05


@dataclass(frozen=True)
class Quad:
    top_left: Point
    top_right: Point
    bottom_right: Point
    bottom_left: Point

    def __post_init__(self) -> None:
        points = self.points
        if any(not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) for x, y in points):
            raise ValueError("Corners must lie inside the photo")
        turns = [_cross(points[i], points[(i + 1) % 4], points[(i + 2) % 4]) for i in range(4)]
        if not all(t > 0 for t in turns):
            raise ValueError("Corners must go clockwise around a convex wall outline")
        if self.area < MIN_AREA_FRACTION:
            raise ValueError("The wall outline covers too little of the photo")

    @classmethod
    def full_frame(cls) -> "Quad":
        return cls((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))

    @classmethod
    def from_list(cls, corners: list[list[float]]) -> "Quad":
        if len(corners) != 4 or any(len(c) != 2 for c in corners):
            raise ValueError("A wall outline needs four [x, y] corners")
        tl, tr, br, bl = ((float(c[0]), float(c[1])) for c in corners)
        return cls(tl, tr, br, bl)

    @property
    def points(self) -> tuple[Point, Point, Point, Point]:
        return (self.top_left, self.top_right, self.bottom_right, self.bottom_left)

    @property
    def area(self) -> float:
        points = self.points
        twice_area = sum(
            points[i][0] * points[(i + 1) % 4][1] - points[(i + 1) % 4][0] * points[i][1] for i in range(4)
        )
        return abs(twice_area) / 2

    def as_list(self) -> list[list[float]]:
        return [[x, y] for x, y in self.points]


def _cross(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
