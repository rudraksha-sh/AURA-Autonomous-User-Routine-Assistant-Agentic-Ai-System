import secrets

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(secret: str) -> Settings:
    return Settings(
        environment="production",
        database_url="sqlite://",
        openrouter_api_key="test-key",
        jwt_secret_key=secret,
        google_client_id="test-client",
        google_client_secret="test-secret",
        google_redirect_uri="http://localhost/callback",
        email_provider="smtp",
        smtp_host="smtp.example.test",
    )


def test_production_rejects_weak_or_placeholder_jwt_secret():
    for secret in ("short", "replace-with-a-unique-random-secret", "your-jwt-secret-key"):
        with pytest.raises(ValidationError):
            _settings(secret)


def test_production_accepts_a_long_unique_jwt_secret():
    generated_secret = secrets.token_urlsafe(48)
    assert _settings(generated_secret).jwt_secret_key == generated_secret


def test_production_rejects_console_email_provider():
    with pytest.raises(ValidationError, match="EMAIL_PROVIDER=console"):
        Settings(
            environment="production",
            database_url="sqlite://",
            jwt_secret_key=secrets.token_urlsafe(48),
            google_client_id="test-client",
            google_client_secret="test-secret",
            google_redirect_uri="http://localhost/callback",
        )
