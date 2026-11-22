import logging
import os
import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.pool import StaticPool

from app.core import rate_limit_dependencies as limits
from app.core.rate_limit import RateLimiter
from app.db.session import Base, SessionLocal
from app.main import app


postgres_url = os.environ.get("AURA_TEST_POSTGRES_URL")
schema = f"aura_test_{uuid4().hex}"
if postgres_url:
    parsed = make_url(postgres_url)
    if (parsed.drivername != "postgresql+psycopg" or parsed.host not in {"127.0.0.1", "::1"}
            or parsed.database != "aura_workflow_test" or not parsed.port or parsed.query):
        raise RuntimeError("Use a loopback PostgreSQL scratch database named aura_workflow_test.")
    test_engine = create_engine(parsed, connect_args={"options": f"-csearch_path={schema} -c timezone=UTC"}, hide_parameters=True)
else:
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )


@pytest.fixture(scope="session", autouse=True)
def test_namespace():
    if postgres_url:
        with test_engine.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA {schema}"))
    yield
    if postgres_url:
        with test_engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))
    test_engine.dispose()


@pytest.fixture(autouse=True)
def isolate_api_tests(monkeypatch):
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    monkeypatch.setitem(SessionLocal.kw, "bind", test_engine)
    limiters = [value for value in vars(limits).values() if isinstance(value, RateLimiter)]
    for limiter in limiters:
        limiter.reset()
    yield
    for limiter in limiters:
        limiter.reset()


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


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
