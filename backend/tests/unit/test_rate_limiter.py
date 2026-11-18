import pytest

from sadu.shared.errors import TooManyRequests
from sadu.shared.web import FORGET_IDLE_EVERY_CHECKS, RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_blocks_after_the_limit_and_frees_the_window():
    clock = FakeClock()
    limiter = RateLimiter(clock)
    for _ in range(3):
        limiter.check("read:1.2.3.4", limit=3, window_s=60)
    with pytest.raises(TooManyRequests):
        limiter.check("read:1.2.3.4", limit=3, window_s=60)
    clock.now += 61
    limiter.check("read:1.2.3.4", limit=3, window_s=60)


def test_keys_do_not_share_a_budget():
    limiter = RateLimiter(FakeClock())
    limiter.check("login:1.1.1.1", limit=1, window_s=60)
    limiter.check("login:2.2.2.2", limit=1, window_s=60)
    with pytest.raises(TooManyRequests):
        limiter.check("login:1.1.1.1", limit=1, window_s=60)


def test_forgets_idle_visitors_so_memory_stays_bounded():
    clock = FakeClock()
    limiter = RateLimiter(clock)
    for visitor in range(FORGET_IDLE_EVERY_CHECKS - 1):
        limiter.check(f"read:10.0.{visitor // 256}.{visitor % 256}", limit=5, window_s=60)
    limiter.check("upload-passport-day:p1", limit=60, window_s=86400)
    assert limiter.tracked_keys == FORGET_IDLE_EVERY_CHECKS

    clock.now += 120
    for _ in range(FORGET_IDLE_EVERY_CHECKS):
        limiter.check("read:9.9.9.9", limit=10**6, window_s=60)

    assert limiter.tracked_keys == 2
    with pytest.raises(TooManyRequests):
        for _ in range(60):
            limiter.check("upload-passport-day:p1", limit=60, window_s=86400)
