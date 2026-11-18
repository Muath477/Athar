import numpy as np

from sadu.modules.watch.domain.scene import Band, Reflectance


def normalized_difference(a: Reflectance, b: Reflectance) -> Reflectance:
    total = a + b
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(total != 0, (a - b) / total, np.nan)
    return np.asarray(result, dtype=np.float32)


def ndvi(bands: dict[Band, Reflectance]) -> Reflectance:
    return normalized_difference(bands[Band.NIR], bands[Band.RED])


def mndwi(bands: dict[Band, Reflectance]) -> Reflectance:
    return normalized_difference(bands[Band.GREEN], bands[Band.SWIR16])


def ndbi(bands: dict[Band, Reflectance]) -> Reflectance:
    return normalized_difference(bands[Band.SWIR16], bands[Band.NIR])


def bsi(bands: dict[Band, Reflectance]) -> Reflectance:
    return normalized_difference(bands[Band.SWIR16] + bands[Band.RED], bands[Band.NIR] + bands[Band.BLUE])


def tgsi(bands: dict[Band, Reflectance]) -> Reflectance:
    total = bands[Band.RED] + bands[Band.BLUE] + bands[Band.GREEN]
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(total != 0, (bands[Band.RED] - bands[Band.BLUE]) / total, np.nan)
    return np.asarray(result, dtype=np.float32)


def brightness(bands: dict[Band, Reflectance]) -> Reflectance:
    visible = np.stack([bands[Band.BLUE], bands[Band.GREEN], bands[Band.RED]])
    return np.asarray(np.sqrt((visible**2).mean(axis=0)), dtype=np.float32)
