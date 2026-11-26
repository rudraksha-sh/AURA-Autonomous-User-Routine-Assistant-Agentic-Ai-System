import secrets

from cryptography.fernet import Fernet
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(secret: str, pepper: str | None = None) -> Settings:
    return Settings(
        environment="production",
        cors_origins="https://app.example.test",
        database_url="postgresql+psycopg://fixture:fixture@localhost/fixture",
        database_ssl_mode="verify-full",
        database_ssl_root_cert="fixture-ca.pem",
        openrouter_api_key="test-key",
        jwt_secret_key=secret,
        otp_pepper=secrets.token_urlsafe(48) if pepper is None else pepper,
        integration_token_key=Fernet.generate_key().decode(),
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
            cors_origins="https://app.example.test",
            database_url="postgresql+psycopg://fixture:fixture@localhost/fixture",
            database_ssl_mode="verify-full",
            database_ssl_root_cert="fixture-ca.pem",
            jwt_secret_key=secrets.token_urlsafe(48),
            otp_pepper=secrets.token_urlsafe(48),
            integration_token_key=Fernet.generate_key().decode(),
            google_client_id="test-client",
            google_client_secret="test-secret",
            google_redirect_uri="http://localhost/callback",
        )


@pytest.mark.parametrize("sample", ["", "replace-with-a-new-otp-pepper", "a" * 64])
def test_production_rejects_insecure_otp_pepper(sample):
    with pytest.raises(ValidationError, match="OTP_PEPPER"):
        _settings(secrets.token_urlsafe(48), sample)


def test_production_rejects_reuse_of_jwt_secret_for_otp():
    shared = secrets.token_urlsafe(48)
    with pytest.raises(ValidationError, match="OTP_PEPPER"):
        _settings(shared, shared)
