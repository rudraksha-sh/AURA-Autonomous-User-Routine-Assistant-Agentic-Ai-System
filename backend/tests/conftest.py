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
if postgres_url:
    parsed = make_url(postgres_url)
    if (parsed.drivername != "postgresql+psycopg" or parsed.host != "127.0.0.1"
            or parsed.database != "aura_workflow_test" or parsed.username != "aura_test"
            or parsed.port != 15432 or parsed.query):
        raise RuntimeError("Use aura_test on the disposable aura_workflow_test database at 127.0.0.1:15432.")
    base_engine = create_engine(parsed, hide_parameters=True)
else:
    base_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )


@pytest.fixture
def test_namespace():
    if postgres_url:
        schema = f"aura_test_{uuid4().hex}"
        if not re.fullmatch(r"aura_test_[0-9a-f]{32}", schema):
            raise RuntimeError("Refusing unsafe PostgreSQL test schema name.")
        test_engine = None
        sentinel = f"aura_fixture_sentinel_{schema.removeprefix('aura_test_')}"
        quote = base_engine.dialect.identifier_preparer.quote
        schema_sql, sentinel_sql = quote(schema), quote(sentinel)
        created = False
        try:
            with base_engine.begin() as conn:
                identity = conn.execute(text(
                    "select current_database(), current_user, inet_server_port()"
                )).one()
                # Docker publishes host port 15432 while PostgreSQL listens on 5432.
                if identity != ("aura_workflow_test", "aura_test", 5432):
                    raise RuntimeError("PostgreSQL fixture connected to an unexpected database.")
                vector_available = conn.execute(text(
                    "select exists (select 1 from pg_extension e join pg_namespace n "
                    "on n.oid = e.extnamespace where e.extname = 'vector' and n.nspname = 'public')"
                )).scalar_one()
                if not vector_available:
                    raise RuntimeError(
                        "Full PostgreSQL test metadata requires pgvector in the public schema "
                        "of the disposable database."
                    )
                conn.execute(text(f"CREATE SCHEMA {schema_sql}"))
                conn.execute(text(f"CREATE TABLE public.{sentinel_sql} (id integer primary key)"))
            created = True
            test_engine = create_engine(
                parsed,
                connect_args={"options": f"-csearch_path={schema},public -c timezone=UTC"},
                hide_parameters=True,
            ).execution_options(schema_translate_map={None: schema})
            yield test_engine.execution_options(
                schema_translate_map={None: schema},
            )
        finally:
            if test_engine is not None:
                test_engine.dispose()
            if created:
                with base_engine.begin() as conn:
                    conn.execute(text(f"DROP SCHEMA {schema_sql} CASCADE"))
                    assert conn.execute(text(
                        "select count(*) from pg_class c join pg_namespace n "
                        "on n.oid=c.relnamespace where n.nspname = :schema and c.relname = :name"
                    ), {"schema": "public", "name": sentinel}).scalar() == 1
                    conn.execute(text(f"DROP TABLE public.{sentinel_sql}"))
    else:
        yield base_engine


@pytest.fixture(autouse=True)
def isolate_api_tests(monkeypatch, test_namespace):
    test_engine = test_namespace
    if not postgres_url:
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
def test_engine(test_namespace):
    return test_namespace


@pytest.fixture
def test_schema(test_engine):
    if test_engine.dialect.name == "sqlite":
        return None
    with test_engine.connect() as connection:
        return connection.execute(text("select current_schema()")).scalar()


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
