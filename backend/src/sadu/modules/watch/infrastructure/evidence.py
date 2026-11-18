from dataclasses import dataclass

import cv2
import numpy as np
import numpy.typing as npt

from sadu.modules.watch.domain.change import THREAT_COLORS, Threat
from sadu.modules.watch.domain.geometry import Zones
from sadu.modules.watch.domain.scene import Band, Composite, Mask

REFLECTANCE_STRETCH = 0.4
UPSCALE = 6
OUTLINE_BGR = (255, 255, 255)
RING_BGR = (200, 200, 200)


def _bgr(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.removeprefix("#")
    return int(value[4:6], 16), int(value[2:4], 16), int(value[0:2], 16)


THREAT_BGR = {threat: _bgr(color) for threat, color in THREAT_COLORS.items()}


@dataclass(frozen=True)
class EvidenceImages:
    before_png: bytes
    after_png: bytes
    change_png: bytes


def render(baseline: Composite, recent: Composite, masks: dict[Threat, Mask], zones: Zones) -> EvidenceImages:
    before = _true_colour(baseline)
    after = _true_colour(recent)
    change = after.copy()
    for threat, mask in masks.items():
        if mask.any():
            tint = np.zeros_like(change)
            tint[:] = THREAT_BGR[threat]
            change = np.where(mask[..., None], cv2.addWeighted(change, 0.35, tint, 0.65, 0), change)
    return EvidenceImages(
        _encode(_outline(before, zones)), _encode(_outline(after, zones)), _encode(_outline(change, zones))
    )


def _true_colour(composite: Composite) -> npt.NDArray[np.uint8]:
    rgb = np.stack(
        [composite.bands[Band.BLUE], composite.bands[Band.GREEN], composite.bands[Band.RED]], axis=-1
    )
    scaled = np.nan_to_num(rgb / REFLECTANCE_STRETCH, nan=0.0)
    return np.asarray(np.clip(scaled * 255, 0, 255), dtype=np.uint8)


def _outline(image: npt.NDArray[np.uint8], zones: Zones) -> npt.NDArray[np.uint8]:
    size = (image.shape[1] * UPSCALE, image.shape[0] * UPSCALE)
    large = cv2.resize(image, size, interpolation=cv2.INTER_NEAREST)
    for mask, colour, thickness in ((zones.inside | zones.ring, RING_BGR, 1), (zones.inside, OUTLINE_BGR, 2)):
        scaled = cv2.resize(mask.astype(np.uint8) * 255, size, interpolation=cv2.INTER_NEAREST)
        contours, _ = cv2.findContours(scaled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(large, contours, -1, colour, thickness, cv2.LINE_AA)
    return np.asarray(large, dtype=np.uint8)


def _encode(image: npt.NDArray[np.uint8]) -> bytes:
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("Could not encode evidence image")
    return bytes(buffer.tobytes())
