from datetime import datetime, timedelta
from enum import StrEnum

CREDENTIAL_ENV_PATTERN = r"^SADU_CAMERA_SECRET_[A-Z0-9_]{1,60}$"


class DeviceKind(StrEnum):
    FIXED_CAMERA = "fixed_camera"
    DRONE = "drone"
    PHONE = "phone"
    UPLOAD = "upload"


class CaptureStatus(StrEnum):
    OK = "ok"
    FAILED = "failed"


def capture_due(last_capture_at: datetime | None, interval: timedelta, now: datetime) -> bool:
    return last_capture_at is None or now - last_capture_at >= interval
