import secrets
import time
from threading import Lock
from urllib.parse import urlencode

from app.core.config import settings
from app.core.shared_security import PostgresOAuthStateStore, security_engine


class OAuthStateStore:
    def __init__(self, ttl_seconds: int = 600):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than 0")

        self.ttl_seconds = ttl_seconds
        self._states: dict[str, tuple[int, float, tuple[str, ...] | None]] = {}
        self._lock = Lock()

    def create(self, user_id: int, scopes: tuple[str, ...] | None = None) -> str:
        state = secrets.token_urlsafe(32)
        expires_at = time.monotonic() + self.ttl_seconds

        with self._lock:
            now = time.monotonic()
            if len(self._states) >= 4096:
                self._states = {key: value for key, value in self._states.items() if value[1] > now}
                if len(self._states) >= 4096:
                    raise ValueError("OAuth connection capacity reached. Try again shortly.")
            self._states[state] = (user_id, expires_at, scopes)

        return state

    def consume(self, state: str) -> int | None:
        grant = self.consume_grant(state)
        return grant[0] if grant else None

    def consume_grant(self, state: str) -> tuple[int, tuple[str, ...] | None] | None:
        now = time.monotonic()

        with self._lock:
            stored = self._states.pop(state, None)

        if stored is None:
            return None

        user_id, expires_at, scopes = stored

        if expires_at <= now:
            return None

        return user_id, scopes

    def reset(self) -> None:
        with self._lock:
            self._states.clear()


oauth_state_store = PostgresOAuthStateStore(security_engine) if security_engine else OAuthStateStore()


GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"

GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.freebusy",
    "https://www.googleapis.com/auth/drive.readonly",
]


def build_google_authorization_url(state: str, scopes: tuple[str, ...] | None = None) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes or GOOGLE_OAUTH_SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }

    return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"