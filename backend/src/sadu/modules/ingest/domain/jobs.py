from datetime import timedelta
from enum import StrEnum

MAX_ATTEMPTS = 3
FIRST_RETRY_DELAY = timedelta(minutes=1)


class JobStatus(StrEnum):
    QUEUED = "queued"
    ANALYSING = "analysing"
    NEEDS_FACADE = "needs_facade"
    DONE = "done"
    FAILED = "failed"


class FacadeMatch(StrEnum):
    CHOSEN = "chosen"
    DEVICE = "device"
    GPS = "gps"


def retry_delay(attempts: int) -> timedelta | None:
    if attempts >= MAX_ATTEMPTS:
        return None
    delay: timedelta = FIRST_RETRY_DELAY * 2 ** max(attempts - 1, 0)
    return delay
