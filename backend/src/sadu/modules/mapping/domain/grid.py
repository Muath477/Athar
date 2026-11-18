from collections.abc import Iterator
from dataclasses import dataclass

ROW_LETTERS = "ABCDEFGHIJKLMNOPQRST"
MIN_COLS = 4
MAX_COLS = 16


@dataclass(frozen=True, order=True)
class CellRef:
    row: int
    col: int

    @property
    def label(self) -> str:
        return f"{ROW_LETTERS[self.row]}{self.col + 1}"


@dataclass(frozen=True)
class Box:
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        inside = all(0.0 <= v <= 1.0 for v in (self.x0, self.y0, self.x1, self.y1))
        if not inside or self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError(f"Box must lie inside the unit square with positive size: {self}")

    @classmethod
    def clipped(cls, x0: float, y0: float, x1: float, y1: float) -> "Box | None":
        x0, y0, x1, y1 = (min(1.0, max(0.0, v)) for v in (x0, y0, x1, y1))
        if x1 <= x0 or y1 <= y0:
            return None
        return cls(x0, y0, x1, y1)


@dataclass(frozen=True)
class WallSize:
    width_m: float
    height_m: float

    def __post_init__(self) -> None:
        if self.width_m <= 0 or self.height_m <= 0:
            raise ValueError("Wall width and height must be positive")

    @property
    def aspect(self) -> float:
        return self.width_m / self.height_m


@dataclass(frozen=True)
class Grid:
    rows: int
    cols: int

    def __post_init__(self) -> None:
        if not 1 <= self.rows <= len(ROW_LETTERS) or not 1 <= self.cols <= MAX_COLS:
            raise ValueError(f"Unsupported grid size {self.rows}x{self.cols}")

    @classmethod
    def for_wall(cls, wall: WallSize, rows: int) -> "Grid":
        cols = min(MAX_COLS, max(MIN_COLS, round(rows * wall.aspect)))
        return cls(rows, cols)

    def cells(self) -> Iterator[CellRef]:
        for row in range(self.rows):
            for col in range(self.cols):
                yield CellRef(row, col)

    def contains(self, ref: CellRef) -> bool:
        return 0 <= ref.row < self.rows and 0 <= ref.col < self.cols

    def parse(self, label: str) -> CellRef:
        label = label.strip().upper()
        if len(label) < 2 or label[0] not in ROW_LETTERS or not label[1:].isdigit():
            raise ValueError(f"Not a cell label: {label!r}")
        ref = CellRef(ROW_LETTERS.index(label[0]), int(label[1:]) - 1)
        if not self.contains(ref):
            raise ValueError(f"Cell {label} is outside a {self.rows}x{self.cols} grid")
        return ref

    def cell_area_m2(self, wall: WallSize) -> float:
        return (wall.width_m / self.cols) * (wall.height_m / self.rows)

    def coverage(self, box: Box) -> dict[CellRef, float]:
        cell_w, cell_h = 1.0 / self.cols, 1.0 / self.rows
        covered: dict[CellRef, float] = {}
        for row in range(int(box.y0 / cell_h), min(self.rows, int(box.y1 / cell_h) + 1)):
            for col in range(int(box.x0 / cell_w), min(self.cols, int(box.x1 / cell_w) + 1)):
                overlap_w = min(box.x1, (col + 1) * cell_w) - max(box.x0, col * cell_w)
                overlap_h = min(box.y1, (row + 1) * cell_h) - max(box.y0, row * cell_h)
                if overlap_w > 0 and overlap_h > 0:
                    covered[CellRef(row, col)] = (overlap_w * overlap_h) / (cell_w * cell_h)
        return covered
