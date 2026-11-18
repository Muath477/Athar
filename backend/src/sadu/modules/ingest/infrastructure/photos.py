import importlib
import importlib.util
import io
import math
from datetime import datetime
from functools import lru_cache
from typing import Any

from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

from sadu.modules.ingest.domain.geo import GeoPoint, PhotoMetadata
from sadu.shared.errors import SaduError

HEIC_BRANDS = frozenset({b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"})
EXIF_TIME_FORMAT = "%Y:%m:%d %H:%M:%S"
CONVERTED_JPEG_QUALITY = 95


def is_heic(raw: bytes) -> bool:
    return len(raw) >= 12 and raw[4:8] == b"ftyp" and raw[8:12] in HEIC_BRANDS


@lru_cache
def heic_supported() -> bool:
    if importlib.util.find_spec("pillow_heif") is None:
        return False
    importlib.import_module("pillow_heif").register_heif_opener()
    return True


def require_supported_format(raw: bytes, file_name: str) -> None:
    if is_heic(raw) and not heic_supported():
        raise SaduError("heic_unsupported", status=415, file_name=file_name)


def as_jpeg_or_png(raw: bytes) -> bytes:
    if not is_heic(raw):
        return raw
    require_supported_format(raw, "")
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=CONVERTED_JPEG_QUALITY)
    return buffer.getvalue()


def read_photo_metadata(raw: bytes) -> PhotoMetadata:
    try:
        exif = Image.open(io.BytesIO(raw)).getexif()
    except (UnidentifiedImageError, OSError):
        return PhotoMetadata()
    return PhotoMetadata(
        location=_location(exif.get_ifd(ExifTags.IFD.GPSInfo)),
        taken_at=_taken_at(exif.get_ifd(ExifTags.IFD.Exif)),
    )


def _location(gps: dict[int, Any]) -> GeoPoint | None:
    try:
        lat = _degrees(gps[ExifTags.GPS.GPSLatitude], gps[ExifTags.GPS.GPSLatitudeRef], "S")
        lon = _degrees(gps[ExifTags.GPS.GPSLongitude], gps[ExifTags.GPS.GPSLongitudeRef], "W")
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return None
    if abs(lat) > 90 or abs(lon) > 180 or (lat == 0 and lon == 0):
        return None
    return GeoPoint(lat, lon)


def _degrees(dms: tuple[Any, Any, Any], ref: Any, negative_ref: str) -> float:
    degrees, minutes, seconds = (float(part) for part in dms)
    value = degrees + minutes / 60 + seconds / 3600
    if isinstance(ref, bytes):
        ref = ref.decode("ascii", "ignore")
    return -value if str(ref).strip().upper() == negative_ref else value


def _taken_at(exif: dict[int, Any]) -> datetime | None:
    stamp = exif.get(ExifTags.Base.DateTimeOriginal)
    if not isinstance(stamp, str):
        return None
    offset = exif.get(ExifTags.Base.OffsetTimeOriginal)
    try:
        if isinstance(offset, str) and offset.strip():
            return datetime.strptime(f"{stamp.strip()} {offset.strip()}", f"{EXIF_TIME_FORMAT} %z")
        return datetime.strptime(stamp.strip(), EXIF_TIME_FORMAT)
    except ValueError:
        return None
