import io

import cv2
import numpy as np
import pytest
from PIL import Image
from skimage import data

from sadu.modules.capture.infrastructure.image_processing import (
    MAX_UPLOAD_BYTES,
    blur_faces,
    process_upload,
)
from sadu.shared.errors import SaduError

GPS_IFD = 0x8825


def jpeg_with_gps(rgb: np.ndarray) -> bytes:
    image = Image.fromarray(rgb)
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"
    exif[GPS_IFD] = {1: "N", 2: (24.0, 44.0, 0.0), 3: "E", 4: (46.0, 34.0, 0.0)}
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def test_exif_and_gps_are_removed() -> None:
    raw = jpeg_with_gps(data.astronaut())
    assert Image.open(io.BytesIO(raw)).getexif()

    stored = Image.open(io.BytesIO(process_upload(raw).jpeg))
    assert not stored.getexif()
    assert "exif" not in stored.info
    assert "icc_profile" not in stored.info


def test_face_is_blurred() -> None:
    bgr = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    original = bgr.copy()
    assert blur_faces(bgr) >= 1
    assert not np.array_equal(original, bgr)


def test_wall_without_people_is_unchanged() -> None:
    wall = np.full((400, 600, 3), (95, 140, 180), dtype=np.uint8)
    assert blur_faces(wall.copy()) == 0


def test_large_images_are_resized() -> None:
    big = np.zeros((3000, 4000, 3), dtype=np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(big).save(buffer, format="PNG")
    processed = process_upload(buffer.getvalue())
    assert max(processed.width, processed.height) == 1600


@pytest.mark.parametrize("raw", [b"not an image", b"GIF89a" + b"\x00" * 100])
def test_non_images_are_rejected(raw: bytes) -> None:
    with pytest.raises(SaduError) as error:
        process_upload(raw)
    assert error.value.status == 415


def test_gif_is_rejected() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="GIF")
    with pytest.raises(SaduError):
        process_upload(buffer.getvalue())


def test_oversized_upload_is_rejected() -> None:
    with pytest.raises(SaduError) as error:
        process_upload(b"\xff" * (MAX_UPLOAD_BYTES + 1))
    assert error.value.status == 413
