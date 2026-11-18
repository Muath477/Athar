from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

import numpy as np
import numpy.typing as npt

Reflectance = npt.NDArray[np.float32]
Mask = npt.NDArray[np.bool_]


class Band(StrEnum):
    BLUE = "blue"
    GREEN = "green"
    RED = "red"
    NIR = "nir"
    SWIR16 = "swir16"
    SWIR22 = "swir22"


@dataclass(frozen=True)
class Window:
    size_px: int
    pixel_m: float = 10.0

    @property
    def half_extent_m(self) -> float:
        return self.size_px * self.pixel_m / 2

    @property
    def pixel_area_m2(self) -> float:
        return self.pixel_m * self.pixel_m


@dataclass(frozen=True)
class Scene:
    acquired_on: date
    bands: dict[Band, Reflectance]
    clear: Mask

    def __post_init__(self) -> None:
        missing = set(Band) - set(self.bands)
        if missing:
            raise ValueError(f"Scene from {self.acquired_on} lacks bands {sorted(missing)}")
        shapes = {array.shape for array in self.bands.values()} | {self.clear.shape}
        if len(shapes) != 1:
            raise ValueError(f"Scene from {self.acquired_on} mixes shapes {sorted(shapes)}")

    @property
    def shape(self) -> tuple[int, ...]:
        return self.clear.shape


MAD_TO_SIGMA = 1.4826


@dataclass(frozen=True)
class Composite:
    bands: dict[Band, Reflectance]
    spread: dict[Band, Reflectance]
    observations: npt.NDArray[np.int16]
    scene_dates: tuple[date, ...] = field(default=())

    def valid(self, minimum_observations: int) -> Mask:
        return np.asarray(self.observations >= minimum_observations)


def median_composite(scenes: list[Scene]) -> Composite:
    if not scenes:
        raise ValueError("A composite needs at least one scene")
    clear = np.stack([scene.clear for scene in scenes])
    bands = {}
    spread = {}
    for band in Band:
        stack = np.stack([scene.bands[band] for scene in scenes]).astype(np.float32)
        stack[~clear] = np.nan
        with np.errstate(all="ignore"):
            bands[band] = _nanmedian(stack)
            spread[band] = np.asarray(
                MAD_TO_SIGMA * _nanmedian(np.abs(stack - bands[band])), dtype=np.float32
            )
    return Composite(
        bands=bands,
        spread=spread,
        observations=clear.sum(axis=0).astype(np.int16),
        scene_dates=tuple(sorted(scene.acquired_on for scene in scenes)),
    )


def _nanmedian(stack: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
    all_missing = np.all(np.isnan(stack), axis=0)
    filled = np.where(all_missing[None, ...], 0.0, stack)
    median = np.nanmedian(filled, axis=0)
    median[all_missing] = np.nan
    return np.asarray(median, dtype=np.float32)
