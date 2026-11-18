import itertools
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image
from scipy import ndimage

WORK_SIDE_PX = 256
MIN_COMPONENT_PX = 25
MAX_LINE_POINTS = 8
EIGHT_NEIGHBOURS = np.ones((3, 3), dtype=int)

Line = list[tuple[float, float]]


def crack_lines(mask_path: Path) -> list[Line]:
    with Image.open(mask_path) as image:
        gray = image.convert("L")
        gray.thumbnail((WORK_SIDE_PX, WORK_SIDE_PX))
        mask = np.asarray(gray) > 127
    return lines_from_mask(mask)


def lines_from_mask(mask: NDArray[np.bool_]) -> list[Line]:
    height, width = mask.shape
    labelled, count = ndimage.label(mask, structure=EIGHT_NEIGHBOURS)
    lines = []
    for component in range(1, count + 1):
        rows, cols = np.nonzero(labelled == component)
        if rows.size < MIN_COMPONENT_PX:
            continue
        points = np.column_stack(((cols + 0.5) / width, (rows + 0.5) / height))
        lines.append(_principal_path(points))
    return lines


def _principal_path(points: NDArray[np.float64]) -> Line:
    centre = points.mean(axis=0)
    _, _, axes = np.linalg.svd(points - centre, full_matrices=False)
    along = (points - centre) @ axes[0]
    edges = np.linspace(along.min(), along.max(), MAX_LINE_POINTS + 1)
    path: Line = []
    for start, end in itertools.pairwise(edges):
        inside = (along >= start) & (along <= end)
        if inside.any():
            x, y = points[inside].mean(axis=0)
            path.append((round(float(x), 3), round(float(y), 3)))
    if len(path) == 1:
        path.append(path[0])
    return path
