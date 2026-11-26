from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

from pydantic import SecretStr
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.routes import integrations
from app.core.config import settings
from app.core.shared_security import PostgresOAuthStateStore, PostgresRateLimiter, SecurityStateUnavailable
from app.models.security_state import oauth_states, rate_buckets
from app.models.user import User


def race(count, callback):
    barrier = Barrier(count)

    def operation(index):
        barrier.wait(timeout=5)
        return callback(index)

    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(operation, range(count)))


def require_postgres(engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("Shared-state concurrency requires PostgreSQL")


def test_shared_rate_budget_is_atomic_and_expires(test_engine):
    require_postgres(test_engine)
    policy = f"test-{uuid4().hex}"

    def replica():
        return PostgresRateLimiter(test_engine, policy, 5, 60, digest_key="synthetic-test-key", max_keys=1)

    instances = (replica(), replica())
    outcomes = race(12, lambda i: instances[i % 2].allow("synthetic-principal"))
    assert outcomes.count(True) == 5
    assert replica().allow("synthetic-principal") is False
    assert instances[1].allow("another-principal") is False
    with test_engine.begin() as connection:
        digest = connection.scalar(select(rate_buckets.c.principal_digest))
        assert len(digest) == 64 and digest != "synthetic-principal"
        connection.execute(update(rate_buckets).where(rate_buckets.c.policy == policy).values(
            expires_at=func.clock_timestamp() - timedelta(seconds=1),
        ))
    assert replica().allow("another-principal") is True


def test_shared_oauth_state_is_single_use_across_connections_and_expires(test_engine):
    require_postgres(test_engine)
    with Session(test_engine) as db:
        user = User(email="state-test@example.com", name="State test", password_hash="synthetic-fixture")
        db.add(user)
        db.commit()
        owner = user.id

    first, second = PostgresOAuthStateStore(test_engine), PostgresOAuthStateStore(test_engine)
    scopes = ("openid", "https://www.googleapis.com/auth/gmail.readonly")
    state = first.create(owner, scopes)
    with test_engine.connect() as connection:
        digest = connection.scalar(select(oauth_states.c.state_digest))
        assert digest != state and len(digest) == 64
    grants = race(12, lambda i: (first, second)[i % 2].consume_grant(state))
    assert [grant for grant in grants if grant is not None] == [(owner, scopes)]
    assert PostgresOAuthStateStore(test_engine).consume_grant(state) is None

    expired = first.create(owner)
    with test_engine.begin() as connection:
        connection.execute(update(oauth_states).values(
            expires_at=func.clock_timestamp() - timedelta(seconds=1),
        ))
    assert second.consume_grant(expired) is None
    replacement = PostgresOAuthStateStore(test_engine, max_states=1).create(owner)
    assert second.consume_grant(replacement) == (owner, None)


def test_oauth_callback_fails_closed_when_shared_store_is_unavailable(client, monkeypatch):
    def unavailable(_state):
        raise SecurityStateUnavailable

    def unexpected(*args, **kwargs):
        pytest.fail("Provider exchange must not run without a consumed grant")

    monkeypatch.setattr(integrations.oauth_state_store, "consume_grant", unavailable)
    monkeypatch.setattr(integrations, "exchange_google_code", unexpected)
    response = client.get("/api/integrations/google/callback", params={"state": "fixture", "code": "fixture"})
    assert response.status_code == 503
    assert response.json()["error"] == "security_state_unavailable"


def test_ingress_guard_requires_matching_secret_and_ip(client, monkeypatch):
    key = "synthetic-shared-ingress-key-for-tests"
    monkeypatch.setattr(settings, "aura_proxy_shared_secret", SecretStr(key))
    path = "/api/integrations/google/callback"
    assert client.get(path).status_code == 403
    assert client.get(path, headers={"X-Aura-Proxy-Token": key, "X-Aura-Client-IP": "invalid"}).status_code == 503
    assert client.get(path, headers={"X-Aura-Proxy-Token": key, "X-Aura-Client-IP": "192.0.2.1"}).status_code == 400
    assert client.get("/livez").status_code == 200
