import os
import sys
import logging
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text


BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://aura_user:aura_password@localhost:5433/aura_test_db"
)
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["OPENROUTER_API_KEY"] = "test-key"


from app.main import app

from app.core.rate_limit_dependencies import (
    ai_limiter,
    login_limiter,
    register_limiter,
    verify_email_limiter,
)


TEST_DATABASE_URL = os.environ["DATABASE_URL"]

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    login_limiter.reset()
    register_limiter.reset()
    ai_limiter.reset()
    verify_email_limiter.reset()

    yield

    login_limiter.reset()
    register_limiter.reset()
    ai_limiter.reset()
    verify_email_limiter.reset()


@pytest.fixture(autouse=True)
def clean_database():
    with test_engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE agent_runs, tasks, goals, users, integrations "
                "RESTART IDENTITY CASCADE"
            )
        )

    yield


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


class _OtpLogCapture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def register_and_verify_email(client, email, password, name):
    email_logger = logging.getLogger("app.services.email_service")
    otp_handler = _OtpLogCapture()
    previous_level = email_logger.level

    email_logger.setLevel(logging.INFO)
    email_logger.addHandler(otp_handler)

    try:
        registration = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "name": name,
            },
        )
    finally:
        email_logger.removeHandler(otp_handler)
        email_logger.setLevel(previous_level)

    assert registration.status_code == 201, registration.text

    log_text = "\n".join(otp_handler.messages)
    match = re.search(
        r"Use this code to verify your email address:\s*(\d{6})",
        log_text,
    )
    assert match, "Verification OTP was not found in captured test logs"

    verification = client.post(
        "/api/auth/verify-email",
        json={
            "email": email,
            "code": match.group(1),
        },
    )
    assert verification.status_code == 200, verification.text

    return client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
