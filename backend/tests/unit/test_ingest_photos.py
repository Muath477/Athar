import io
from datetime import UTC, datetime, timedelta, timezone

import pytest
from PIL import ExifTags, Image

from sadu.modules.ingest.infrastructure.photos import (
    heic_supported,
    is_heic,
    read_photo_metadata,
    require_supported_format,
)
from sadu.shared.errors import SaduError

HEIC_HEADER = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic"


def photo_with_exif(
    gps: dict[int, object] | None = None, taken: str | None = None, offset: str | None = None
) -> bytes:
    exif = Image.Exif()
    if gps:
        exif.get_ifd(ExifTags.IFD.GPSInfo).update(gps)
    if taken:
        exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = taken
    if offset:
        exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.OffsetTimeOriginal] = offset
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), "tan").save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


def gps(
    lat: tuple[float, float, float], lat_ref: str, lon: tuple[float, float, float], lon_ref: str
) -> dict[int, object]:
    return {
        ExifTags.GPS.GPSLatitudeRef: lat_ref,
        ExifTags.GPS.GPSLatitude: lat,
        ExifTags.GPS.GPSLongitudeRef: lon_ref,
        ExifTags.GPS.GPSLongitude: lon,
    }


def test_gps_and_capture_time_are_read_before_stripping() -> None:
    raw = photo_with_exif(
        gps((24.0, 42.0, 49.0), "N", (46.0, 40.0, 31.08), "E"), "2026:11:10 08:30:00", "+03:00"
    )

    metadata = read_photo_metadata(raw)

    assert metadata.location is not None
    assert metadata.location.lat == pytest.approx(24.713611, abs=1e-6)
    assert metadata.location.lon == pytest.approx(46.6753, abs=1e-6)
    assert metadata.taken_at == datetime(2026, 11, 10, 8, 30, tzinfo=timezone(timedelta(hours=3)))
    assert metadata.taken_at.astimezone(UTC).hour == 5


def test_southern_and_western_references_are_negative() -> None:
    metadata = read_photo_metadata(photo_with_exif(gps((33.0, 51.0, 0.0), "S", (151.0, 12.0, 0.0), "W")))

    assert metadata.location is not None
    assert metadata.location.lat == pytest.approx(-33.85)
    assert metadata.location.lon == pytest.approx(-151.2)


def test_capture_time_without_offset_stays_local() -> None:
    metadata = read_photo_metadata(photo_with_exif(taken="2026:11:10 08:30:00"))

    assert metadata.taken_at == datetime(2026, 11, 10, 8, 30)
    assert metadata.location is None


@pytest.mark.parametrize(
    "raw",
    [
        photo_with_exif(),
        photo_with_exif(gps((0.0, 0.0, 0.0), "N", (0.0, 0.0, 0.0), "E")),
        photo_with_exif({ExifTags.GPS.GPSLatitudeRef: "N"}),
        photo_with_exif(taken="not a date"),
        b"not an image",
    ],
)
def test_missing_or_broken_metadata_is_ignored(raw: bytes) -> None:
    metadata = read_photo_metadata(raw)
    assert metadata.location is None
    assert metadata.taken_at is None


def test_heic_is_recognised_by_its_brand() -> None:
    assert is_heic(HEIC_HEADER)
    assert not is_heic(photo_with_exif())
    assert not is_heic(b"\x00\x00\x00\x18ftypmp42")


@pytest.mark.skipif(heic_supported(), reason="pillow-heif is installed")
def test_heic_without_decoder_is_rejected_in_arabic() -> None:
    with pytest.raises(SaduError) as raised:
        require_supported_format(HEIC_HEADER, "IMG_0001.HEIC")

    assert raised.value.code == "heic_unsupported"
    assert raised.value.status == 415
    assert raised.value.params == {"file_name": "IMG_0001.HEIC"}
