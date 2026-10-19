from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AURA"
    environment: str = "development"

    database_url: str

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

    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
    
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def require_strong_production_jwt_secret(self):
        if self.environment.lower() in {"production", "prod"}:
            if len(self.jwt_secret_key.encode("utf-8")) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 bytes in production")
            if self.jwt_secret_key == "your-jwt-secret-key" or self.jwt_secret_key.startswith("replace-"):
                raise ValueError("JWT_SECRET_KEY must be replaced in production")
            if self.email_provider == "console":
                raise ValueError("EMAIL_PROVIDER=console is not allowed in production")
            if self.email_provider == "smtp" and (not self.smtp_host or not self.email_from):
                raise ValueError("SMTP_HOST and EMAIL_FROM are required when EMAIL_PROVIDER=smtp")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
