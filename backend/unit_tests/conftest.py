import pytest

from app.core import rate_limit_dependencies as limits
from app.core.rate_limit import RateLimiter
from app.api.routes import auth as auth_routes


CAPTURED_EMAIL_CODES: dict[tuple[str, str], str] = {}


@pytest.fixture(autouse=True)
def reset_rate_limiters(monkeypatch):
    CAPTURED_EMAIL_CODES.clear()

    def capture_email_code(email: str, kind: str, code: str | None = None) -> None:
        if code:
            CAPTURED_EMAIL_CODES[(email.lower(), kind)] = code

    monkeypatch.setattr(auth_routes, "send_email_safely", capture_email_code)
    for limiter in vars(limits).values():
        if isinstance(limiter, RateLimiter):
            limiter.reset()
    yield
    for limiter in vars(limits).values():
        if isinstance(limiter, RateLimiter):
            limiter.reset()
