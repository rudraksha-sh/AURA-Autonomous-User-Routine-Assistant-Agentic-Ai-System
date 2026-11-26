"""Use PostgreSQL transactions for shared security state."""
from contextlib import contextmanager
from datetime import timedelta
from hashlib import sha256
import hmac
import secrets

from sqlalchemy import create_engine, delete, func, insert, select, text, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.models.security_state import oauth_states, rate_buckets


class SecurityStateUnavailable(Exception):
    """Security-sensitive operations cannot continue without shared state."""


security_engine = (
    create_engine(
        settings.database_url, pool_size=4, max_overflow=0, pool_timeout=2,
        connect_args={
            "connect_timeout": 3,
            **({"sslmode": settings.database_ssl_mode, "sslrootcert": settings.database_ssl_root_cert}
               if settings.database_ssl_mode != "disable" else {}),
        },
        hide_parameters=True,
    )
    if settings.uses_shared_security_state else None
)


@contextmanager
def transaction(engine: Engine):
    try:
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL statement_timeout = '2s'"))
            connection.execute(text("SET LOCAL lock_timeout = '1s'"))
            yield connection
    except SQLAlchemyError:
        raise SecurityStateUnavailable from None


def lock_policy(connection: Connection, policy: str) -> None:
    connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:policy, 0))"),
                       {"policy": "aura:security:" + policy})


class PostgresRateLimiter:
    def __init__(self, engine: Engine, policy: str, max_requests: int, window_seconds: int,
                 *, digest_key: str, max_keys: int = 16_384):
        self.engine = engine
        self.policy = policy
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.digest_key = digest_key.encode()
        self.max_keys = max_keys

    def allow(self, key: str) -> bool:
        digest = hmac.new(self.digest_key, f"aura:rate:{self.policy}:{key}".encode(), sha256).hexdigest()
        policy = rate_buckets.c.policy == self.policy
        bucket = rate_buckets.c.principal_digest == digest
        window = timedelta(seconds=self.window_seconds)

        with transaction(self.engine) as connection:
            lock_policy(connection, "rate:" + self.policy)
            now = connection.scalar(select(func.clock_timestamp()))
            connection.execute(delete(rate_buckets).where(policy, rate_buckets.c.expires_at <= now))
            hits = connection.scalar(select(rate_buckets.c.hits).where(policy, bucket))
            if hits is None:
                count = connection.scalar(select(func.count()).select_from(rate_buckets).where(policy))
                if count >= self.max_keys:
                    return False
                connection.execute(insert(rate_buckets).values(
                    policy=self.policy, principal_digest=digest, hits=[now.timestamp()],
                    expires_at=now + window,
                ))
                return True

            recent = [hit for hit in hits if hit > (now - window).timestamp()]
            if len(recent) >= self.max_requests:
                return False
            connection.execute(update(rate_buckets).where(policy, bucket).values(
                hits=[*recent, now.timestamp()], expires_at=now + window,
            ))
            return True


class PostgresOAuthStateStore:
    def __init__(self, engine: Engine, ttl_seconds: int = 600, *, max_states: int = 4096):
        self.engine = engine
        self.ttl_seconds = ttl_seconds
        self.max_states = max_states

    def create(self, user_id: int, scopes: tuple[str, ...] | None = None) -> str:
        state = secrets.token_urlsafe(32)
        with transaction(self.engine) as connection:
            lock_policy(connection, "oauth")
            now = connection.scalar(select(func.clock_timestamp()))
            connection.execute(delete(oauth_states).where(oauth_states.c.expires_at <= now))
            count = connection.scalar(select(func.count()).select_from(oauth_states))
            if count >= self.max_states:
                raise ValueError("OAuth connection capacity reached. Try again shortly.")
            connection.execute(insert(oauth_states).values(
                state_digest=sha256(state.encode()).hexdigest(), user_id=user_id,
                scopes=scopes, expires_at=now + timedelta(seconds=self.ttl_seconds),
            ))
        return state

    def consume_grant(self, state: str) -> tuple[int, tuple[str, ...] | None] | None:
        if len(state) > 128:
            return None
        with transaction(self.engine) as connection:
            row = connection.execute(delete(oauth_states).where(
                oauth_states.c.state_digest == sha256(state.encode()).hexdigest(),
                oauth_states.c.expires_at > func.clock_timestamp(),
            ).returning(oauth_states.c.user_id, oauth_states.c.scopes)).one_or_none()
        if row is None:
            return None
        return row.user_id, tuple(row.scopes) if row.scopes is not None else None
