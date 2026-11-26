import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
import jwt
from jwt import InvalidTokenError
from pydantic import BaseModel, ValidationError
import pytest

from app.core.config import Settings, settings
from app.core.exceptions import register_exception_handlers
from app.core.rate_limit import RateLimiter
from app.core.request_size import RequestSizeLimit
from app.core.security import create_access_token, decode_access_token
from app.core.security_headers import register_security_headers


def test_signed_token_requires_expiration():
    versioned_claims = {"sub": "1", "ver": 0}
    assert decode_access_token(create_access_token(versioned_claims))["sub"] == "1"
    incomplete = jwt.encode(versioned_claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(InvalidTokenError):
        decode_access_token(incomplete)


def test_rate_limit_capacity_preserves_current_budgets_and_expires_idle_keys(monkeypatch):
    now = 0.0
    monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: now)
    limiter = RateLimiter(2, 10, max_keys=2)
    assert limiter.allow("first")
    assert limiter.allow("second")
    assert not limiter.allow("new")
    now = 5.0
    assert limiter.allow("first")
    assert not limiter.allow("first")
    now = 10.0
    assert limiter.allow("new")
    assert limiter.allow("first")
    assert not limiter.allow("first")


@pytest.mark.parametrize("origin", ["*", "http://app.example.com", "https://app.example.com/path"])
def test_production_refuses_inexact_cors_origins(origin):
    with pytest.raises(ValidationError, match="exact HTTPS origins"):
        Settings(environment="production", cors_origins=origin, jwt_secret_key="x" * 36,
                 email_provider="smtp", smtp_host="mail.example.com",
                 database_url="sqlite://", google_client_id="fixture", google_client_secret="fixture",
                 google_redirect_uri="https://api.example.com/api/integrations/google/callback")


def test_body_limit_counts_streamed_and_declared_bytes_before_handler():
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(RequestSizeLimit, max_bytes=16)
    register_security_headers(app)
    calls = []

    class Body(BaseModel):
        value: str

    @app.post("/api/input")
    def accept(body: Body):
        calls.append(body.value)
        return {"accepted": True}

    with TestClient(app) as client:
        accepted = client.post("/api/input", content=b'{"value":"here"}', headers={"Content-Type": "application/json"})
        assert accepted.status_code == 200
        assert accepted.headers["Cache-Control"] == "no-store"
        for content in (b'{"value":"too long"}', iter((b'{"value":', b'"too long"}'))):
            rejected = client.post("/api/input", content=content, headers={"Content-Type": "application/json"})
            assert rejected.status_code == 413
            assert rejected.headers["Cache-Control"] == "no-store"
    assert calls == ["here"]


def test_validation_log_uses_route_template_without_caller_fields(caplog):
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/api/item/{item}")
    def read(item: int):
        return item

    with caplog.at_level(logging.WARNING, logger="aura.api"), TestClient(app) as client:
        response = client.get("/api/item/synthetic-sensitive-path")
    assert response.status_code == 422
    assert "/api/item/{item}" in caplog.text
    assert "synthetic-sensitive-path" not in caplog.text
