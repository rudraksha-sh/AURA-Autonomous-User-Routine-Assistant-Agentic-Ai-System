import pytest

from app.core.rate_limit import RateLimiter


def test_rate_limiter_allows_requests_within_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("client") is True
    assert limiter.allow("client") is True


def test_rate_limiter_blocks_requests_over_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("client") is True
    assert limiter.allow("client") is True
    assert limiter.allow("client") is False


def test_rate_limiter_isolated_by_key():
    limiter = RateLimiter(max_requests=1, window_seconds=60)

    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False
    assert limiter.allow("client-b") is True


def test_rate_limiter_reset():
    limiter = RateLimiter(max_requests=1, window_seconds=60)

    assert limiter.allow("client") is True
    assert limiter.allow("client") is False

    limiter.reset()

    assert limiter.allow("client") is True


def test_rate_limiter_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        RateLimiter(max_requests=0, window_seconds=60)

    with pytest.raises(ValueError):
        RateLimiter(max_requests=1, window_seconds=0)