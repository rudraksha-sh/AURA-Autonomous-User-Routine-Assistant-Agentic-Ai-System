"""Loopback-only E2E backend with a fresh SQLite database and synthetic providers."""
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from urllib.parse import urlencode
import sys

from cryptography.fernet import Fernet
from fastapi import HTTPException
from starlette.responses import HTMLResponse
import uvicorn

FRONTEND = "http://127.0.0.1:3100"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))


def serve(directory):
    os.chdir(directory)
    os.environ.update(
        ENVIRONMENT="development", DATABASE_URL="sqlite:///aura-e2e.db",
        JWT_SECRET_KEY="isolated-e2e-signing-key-for-synthetic-sessions", INTEGRATION_TOKEN_KEY=Fernet.generate_key().decode(),
        AI_PROVIDER="disabled", OPENROUTER_API_KEY="", EMAIL_PROVIDER="console",
        CONTEXT_MODEL_PATH="", GOOGLE_CLIENT_ID="e2e-client", GOOGLE_CLIENT_SECRET="e2e-secret",
        GOOGLE_REDIRECT_URI=FRONTEND + "/api/integrations/google/callback", FRONTEND_URL=FRONTEND,
    )

    from app.agents.execution.adapters import ADAPTERS
    from app.api.routes import integrations
    from app.integrations.google import reads
    from app.integrations.google.oauth import GOOGLE_OAUTH_SCOPES
    from app.main import app
    from app.services.email_service import ConsoleEmailProvider

    assert not ADAPTERS
    messages = {}

    def capture_email(_, to_email, subject, plain, html):
        if subject == "Verify your AURA email":
            messages[to_email] = re.search(r": (\d{6})", plain)[1]

    ConsoleEmailProvider.send = capture_email

    @app.get("/api/e2e/verification-code")
    def verification_code(email: str):
        code = messages.pop(email, None)
        if code is None:
            raise HTTPException(404)
        return {"code": code}

    @app.get("/api/e2e/google-consent", response_class=HTMLResponse)
    def consent(state: str):
        query = urlencode({"code": "fixture-consent", "state": state})
        return '<main><h1>Mock Google consent</h1><a href="/api/integrations/google/callback?' + query + '">Allow read access</a></main>'

    def exchange(code, scopes=None):
        if code != "fixture-consent":
            raise ValueError("Unexpected mock OAuth code")
        return SimpleNamespace(token="fixture-access", refresh_token="fixture-refresh",
                               expiry=datetime.now(timezone.utc) + timedelta(hours=1),
                               scopes=scopes or GOOGLE_OAUTH_SCOPES)

    def mock_read(method, url, token, **options):
        if url.endswith("/freeBusy"):
            return {"calendars": {"primary": {"busy": []}}}
        raise ValueError("Unexpected mock provider request")

    integrations.build_google_authorization_url = lambda state, scopes: (
        FRONTEND + "/api/e2e/google-consent?" + urlencode({"state": state})
    )
    integrations.exchange_google_code = exchange
    integrations.get_google_user_info = lambda credentials: {"id": "fixture-account"}
    reads._request = mock_read
    reads.revoke = lambda integration: None

    uvicorn.run(app, host="127.0.0.1", port=8100, access_log=False)


if __name__ == "__main__":
    with TemporaryDirectory(prefix="aura-e2e-") as directory:
        try:
            serve(directory)
        finally:
            os.chdir(Path(__file__).resolve().parent)
