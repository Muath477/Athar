from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
from scipy import ndimage

from sadu.modules.watch.domain import indices
from sadu.modules.watch.domain.geometry import Zones
from sadu.modules.watch.domain.scene import Band, Composite, Mask, Reflectance, Window

EIGHT_NEIGHBOURS = np.ones((3, 3), dtype=bool)


class Threat(StrEnum):
    WATER = "water"
    VEGETATION_LOSS = "vegetation_loss"
    CONSTRUCTION = "construction"
    EARTHWORKS = "earthworks"
    SAND = "sand"


class Zone(StrEnum):
    INSIDE = "inside"
    RING = "ring"


THREAT_COLORS: dict[Threat, str] = {
    Threat.WATER: "#3498db",
    Threat.VEGETATION_LOSS: "#3ca03c",
    Threat.CONSTRUCTION: "#c0392b",
    Threat.EARTHWORKS: "#e67e22",
    Threat.SAND: "#b7950b",
}


class ScreeningStatus(StrEnum):
    OK = "ok"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class ChangeRules:
    minimum_baseline_observations: int = 8
    minimum_recent_observations: int = 3
    minimum_valid_share: float = 0.6
    minimum_cluster_pixels: int = 3
    change_z: float = 3.0
    spread_floor: float = 0.01
    water_mndwi_after: float = 0.0
    water_mndwi_before: float = -0.1
    vegetation_baseline_ndvi: float = 0.3
    vegetation_ndvi_drop: float = 0.15
    vegetation_relative_drop: float = 0.3
    construction_ndbi_rise: float = 0.10
    asphalt_brightness: float = 0.10
    asphalt_darkening: float = 0.05
    sand_tgsi_rise: float = 0.05


@dataclass(frozen=True)
class Signal:
    threat: Threat
    zone: Zone
    changed_pixels: int
    zone_pixels: int
    area_m2: float

    @property
    def share(self) -> float:
        return self.changed_pixels / self.zone_pixels if self.zone_pixels else 0.0


@dataclass(frozen=True)
class ChangeReport:
    status: ScreeningStatus
    valid_share: float
    signals: tuple[Signal, ...]
    masks: dict[Threat, Mask] = field(default_factory=dict)

    def strongest(self) -> Signal | None:
        return max(self.signals, key=lambda s: s.area_m2, default=None)


def detect_changes(
    baseline: Composite, recent: Composite, zones: Zones, window: Window, rules: ChangeRules
) -> ChangeReport:
    watched = zones.inside | zones.ring
    valid = (
        baseline.valid(rules.minimum_baseline_observations)
        & recent.valid(rules.minimum_recent_observations)
        & watched
    )
    valid_share = float(valid.sum() / watched.sum()) if watched.any() else 0.0
    if valid_share < rules.minimum_valid_share:
        return ChangeReport(ScreeningStatus.INSUFFICIENT_DATA, valid_share, ())

    masks = _classify(baseline, recent, valid, rules)
    signals = []
    for threat, mask in masks.items():
        for zone, zone_mask in ((Zone.INSIDE, zones.inside), (Zone.RING, zones.ring)):
            changed = int((mask & zone_mask).sum())
            if changed:
                signals.append(
                    Signal(threat, zone, changed, int(zone_mask.sum()), changed * window.pixel_area_m2)
                )
    return ChangeReport(ScreeningStatus.OK, valid_share, tuple(signals), masks)


def change_magnitude(baseline: Composite, recent: Composite, spread_floor: float) -> Reflectance:
    squared = [
        ((recent.bands[band] - baseline.bands[band]) / np.maximum(baseline.spread[band], spread_floor)) ** 2
        for band in Band
    ]
    with np.errstate(invalid="ignore"):
        return np.asarray(np.sqrt(np.mean(squared, axis=0)), dtype=np.float32)


def keep_clusters(mask: Mask, minimum_pixels: int) -> Mask:
    labels, count = ndimage.label(mask, structure=EIGHT_NEIGHBOURS)
    if count == 0:
        return np.zeros(mask.shape, dtype=bool)
    sizes = np.bincount(labels.ravel())
    large = sizes >= minimum_pixels
    large[0] = False
    return np.asarray(large[labels])


def _classify(baseline: Composite, recent: Composite, valid: Mask, rules: ChangeRules) -> dict[Threat, Mask]:
    before, after = baseline.bands, recent.bands
    with np.errstate(invalid="ignore", divide="ignore"):
        water = (indices.mndwi(after) > rules.water_mndwi_after) & (
            indices.mndwi(before) < rules.water_mndwi_before
        )
        ndvi_before = indices.ndvi(before)
        ndvi_drop = indices.ndvi(after) - ndvi_before
        vegetation_loss = (
            (ndvi_before >= rules.vegetation_baseline_ndvi)
            & (ndvi_drop <= -rules.vegetation_ndvi_drop)
            & (ndvi_drop / ndvi_before <= -rules.vegetation_relative_drop)
        )
        changed = change_magnitude(baseline, recent, rules.spread_floor) >= rules.change_z
        brightness_after = indices.brightness(after)
        brightness_change = brightness_after - indices.brightness(before)
        asphalt = (brightness_after < rules.asphalt_brightness) & (
            brightness_change <= -rules.asphalt_darkening
        )
        construction = changed & (
            (indices.ndbi(after) - indices.ndbi(before) > rules.construction_ndbi_rise) | asphalt
        )
        sand = (
            changed
            & (indices.tgsi(after) - indices.tgsi(before) > rules.sand_tgsi_rise)
            & (brightness_change > 0)
        )

    claimed = np.zeros(valid.shape, dtype=bool)
    masks: dict[Threat, Mask] = {}
    for threat, candidate in (
        (Threat.WATER, water),
        (Threat.VEGETATION_LOSS, vegetation_loss),
        (Threat.CONSTRUCTION, construction),
        (Threat.SAND, sand),
        (Threat.EARTHWORKS, changed),
    ):
        mask = keep_clusters(np.asarray(candidate & valid & ~claimed), rules.minimum_cluster_pixels)
        masks[threat] = mask
        claimed |= mask
    return masks
