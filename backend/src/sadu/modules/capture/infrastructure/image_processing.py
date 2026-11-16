"""Process-before-store (ADR-015): nothing below leaves memory until EXIF is gone and faces
are blurred."""

import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageOps, UnidentifiedImageError

from sadu.shared.config import get_settings
from sadu.shared.errors import SaduError

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 40_000_000
STORED_LONG_SIDE_PX = 1600
JPEG_QUALITY = 85
FACE_SCORE_THRESHOLD = 0.6
FACE_PADDING = 0.2
ALLOWED_FORMATS = {"JPEG", "PNG"}

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


@dataclass(frozen=True)
class ProcessedPhoto:
    jpeg: bytes
    width: int
    height: int
    faces_blurred: int


def process_upload(raw: bytes) -> ProcessedPhoto:
    """Validate, orient, strip metadata, resize and blur faces. Raises SaduError on bad input."""
    if len(raw) > MAX_UPLOAD_BYTES:
        raise SaduError("upload_too_large", status=413, max_mb=MAX_UPLOAD_BYTES // (1024 * 1024))
    image = _decode_validated(raw)
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((STORED_LONG_SIDE_PX, STORED_LONG_SIDE_PX), Image.Resampling.LANCZOS)

    bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    faces = blur_faces(bgr)
    # Re-encoding from pixels writes a JPEG with no EXIF, XMP or ICC data.
    ok, buffer = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise SaduError("unsupported_image", status=415)
    height, width = bgr.shape[:2]
    return ProcessedPhoto(buffer.tobytes(), width, height, faces)


def blur_faces(bgr: NDArray[np.uint8]) -> int:
    """Blur every detected face in place and return how many were found."""
    height, width = bgr.shape[:2]
    detector = _face_detector()
    detector.setInputSize((width, height))
    _, detections = detector.detect(bgr)
    if detections is None:
        return 0
    for detection in detections:
        x, y, w, h = (float(v) for v in detection[:4])
        pad_x, pad_y = w * FACE_PADDING, h * FACE_PADDING
        x0, y0 = max(int(x - pad_x), 0), max(int(y - pad_y), 0)
        x1, y1 = min(int(x + w + pad_x), width), min(int(y + h + pad_y), height)
        if x1 <= x0 or y1 <= y0:
            continue
        face = bgr[y0:y1, x0:x1]
        kernel = max((x1 - x0) // 3 | 1, 15)
        bgr[y0:y1, x0:x1] = cv2.GaussianBlur(face, (kernel, kernel), 0)
    return len(detections)


def _decode_validated(raw: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(raw))
        image_format = image.format
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise SaduError("unsupported_image", status=415) from error
    if image_format not in ALLOWED_FORMATS:
        raise SaduError("unsupported_image", status=415)
    return image


@lru_cache
def _face_detector() -> cv2.FaceDetectorYN:
    model_path = Path(get_settings().sadu_yunet_model_path)
    if not model_path.is_file():
        raise RuntimeError(f"Face detection model missing at {model_path}; see backend/README")
    return cv2.FaceDetectorYN.create(str(model_path), "", (320, 320), FACE_SCORE_THRESHOLD, 0.3, 5000)
