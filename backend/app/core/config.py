from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AURA"
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"

    database_url: str
    database_ssl_mode: Literal["disable", "require", "verify-ca", "verify-full"] = "disable"
    database_ssl_root_cert: str = ""
    context_model_path: str = ""
    context_model_revision: str = ""

    openrouter_api_key: str = ""
    ai_model: str = "openai/gpt-4o-mini"
    ai_provider: Literal["openrouter", "disabled"] = "openrouter"
    ai_timeout_seconds: int = Field(default=15, ge=1, le=60)

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    email_provider: Literal["console", "smtp"] = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "AURA <noreply@example.com>"
    otp_expiry_minutes: int = Field(default=10, ge=1, le=60)
    otp_max_attempts: int = Field(default=5, ge=1, le=20)
    otp_resend_cooldown_seconds: int = Field(default=60, ge=1, le=3600)
    otp_pepper: str = ""

    security_state_backend: Literal["memory", "postgres"] | None = None
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
    
    aura_proxy_shared_secret: SecretStr = SecretStr("")
    integration_token_key: SecretStr = SecretStr("")

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    @model_validator(mode="after")
    def require_strong_production_jwt_secret(self):
        key = self.integration_token_key.get_secret_value()
        if key:
            try:
                Fernet(key.encode())
            except ValueError:
                raise ValueError("INTEGRATION_TOKEN_KEY must be a valid Fernet key") from None
        proxy_key = self.aura_proxy_shared_secret.get_secret_value()
        if proxy_key and len(proxy_key.encode()) < 32:
            raise ValueError("AURA_PROXY_SHARED_SECRET must contain at least 32 bytes")
        if self.is_production:
            for origin in self.cors_origin_list:
                parsed = urlsplit(origin)
                if (parsed.scheme != "https" or not parsed.hostname or "*" in parsed.netloc
                        or parsed.username is not None or parsed.path or parsed.query or parsed.fragment):
                    raise ValueError("Production CORS origins must be exact HTTPS origins")
            if len(self.jwt_secret_key.encode("utf-8")) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 bytes in production")
            if self.jwt_secret_key == "your-jwt-secret-key" or self.jwt_secret_key.startswith("replace-"):
                raise ValueError("JWT_SECRET_KEY must be replaced in production")
            if (not re.fullmatch(r"[A-Za-z0-9_-]{64}", self.otp_pepper)
                    or len(set(self.otp_pepper)) < 16
                    or self.otp_pepper == self.jwt_secret_key):
                raise ValueError("OTP_PEPPER must be a fresh independent production secret generated with token_urlsafe(48)")
            if not key:
                raise ValueError("INTEGRATION_TOKEN_KEY is required in production")
            if self.email_provider == "console":
                raise ValueError("EMAIL_PROVIDER=console is not allowed in production")
            if self.email_provider == "smtp" and (not self.smtp_host or not self.email_from):
                raise ValueError("SMTP_HOST and EMAIL_FROM are required when EMAIL_PROVIDER=smtp")
        if self.is_production and not self.uses_shared_security_state:
            raise ValueError("Production requires PostgreSQL shared security state")
        if self.uses_shared_security_state and not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("Shared security state requires a postgresql+psycopg database URL")
        if self.is_production and self.database_url.startswith("postgresql+psycopg://"):
            if self.database_ssl_mode != "verify-full":
                raise ValueError("Production PostgreSQL requires DATABASE_SSL_MODE=verify-full")
            if not self.database_ssl_root_cert:
                raise ValueError("Production PostgreSQL requires DATABASE_SSL_ROOT_CERT")
        return self

    @property
    def uses_shared_security_state(self) -> bool:
        return self.security_state_backend == "postgres" or (
            self.security_state_backend is None and self.is_production
        )

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


secrets_dir = Path("/run/secrets")
settings = Settings(_secrets_dir=secrets_dir if secrets_dir.is_dir() else None)
