import secrets
import time
from threading import Lock


class OAuthStateStore:
    def __init__(self, ttl_seconds: int = 600):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than 0")

        self.ttl_seconds = ttl_seconds
        self._states: dict[str, tuple[int, float]] = {}
        self._lock = Lock()

    def create(self, user_id: int) -> str:
        state = secrets.token_urlsafe(32)
        expires_at = time.monotonic() + self.ttl_seconds

        with self._lock:
            self._states[state] = (user_id, expires_at)

        return state

    def consume(self, state: str) -> int | None:
        now = time.monotonic()

        with self._lock:
            stored = self._states.pop(state, None)

        if stored is None:
            return None

        user_id, expires_at = stored

        if expires_at <= now:
            return None

        return user_id

    def reset(self) -> None:
        with self._lock:
            self._states.clear()


oauth_state_store = OAuthStateStore()

from urllib.parse import urlencode

from app.core.config import settings


GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"

GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def build_google_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_OAUTH_SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }

    return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"