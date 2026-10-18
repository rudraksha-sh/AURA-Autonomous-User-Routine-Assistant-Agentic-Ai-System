import pytest

from app.core.rate_limit_dependencies import ai_limiter, login_limiter, register_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    login_limiter.reset()
    register_limiter.reset()
    ai_limiter.reset()
    yield
    login_limiter.reset()
    register_limiter.reset()
    ai_limiter.reset()
