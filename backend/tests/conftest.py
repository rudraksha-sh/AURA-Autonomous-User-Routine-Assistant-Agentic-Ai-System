import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text


BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://aura_user:aura_password@localhost:5432/aura_test_db"
)
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["OPENROUTER_API_KEY"] = "test-key"


from app.main import app

from app.core.rate_limit_dependencies import (
    ai_limiter,
    login_limiter,
    register_limiter,
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

    yield

    login_limiter.reset()
    register_limiter.reset()
    ai_limiter.reset()


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