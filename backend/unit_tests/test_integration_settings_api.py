from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base, get_db
from app.main import app
from app.models.integration import Integration
from app.models.user import User


def test_google_integration_status_and_disconnect_are_private(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'integrations.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            headers_by_email = {}
            user_ids = {}
            for email in ("connected@example.com", "separate@example.com"):
                register_verified(client, {"name": "Google User", "email": email, "password": "StrongPass123!"})
                token = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"}).json()["access_token"]
                headers_by_email[email] = {"Authorization": f"Bearer {token}"}
            with Session(engine) as db:
                user_ids["connected@example.com"] = db.query(User).filter_by(email="connected@example.com").one().id
                user_ids["separate@example.com"] = db.query(User).filter_by(email="separate@example.com").one().id
                db.add(Integration(
                    user_id=user_ids["connected@example.com"], provider="google", provider_account_id="google-user",
                    access_token="secret-access-token", refresh_token="secret-refresh-token", scopes="calendar.readonly profile",
                    token_expiry=None, last_synced_at=datetime(2026, 10, 19, tzinfo=timezone.utc),
                ))
                db.commit()

            owner = headers_by_email["connected@example.com"]
            separate = headers_by_email["separate@example.com"]
            assert client.get("/api/integrations/google/status").status_code == 401
            assert client.get("/api/integrations/google/status", headers=separate).json() == {"status": "disconnected", "scopes": [], "last_sync_at": None}
            connected = client.get("/api/integrations/google/status", headers=owner)
            assert connected.status_code == 200
            assert connected.json()["status"] == "connected"
            assert connected.json()["scopes"] == ["calendar.readonly", "profile"]
            assert connected.json()["last_sync_at"] == "2026-10-19T00:00:00"
            assert "secret-access-token" not in connected.text
            assert client.delete("/api/integrations/google", headers=separate).status_code == 204
            assert client.get("/api/integrations/google/status", headers=owner).json()["status"] == "connected"
            assert client.delete("/api/integrations/google", headers=owner).status_code == 204
            assert client.get("/api/integrations/google/status", headers=owner).json()["status"] == "disconnected"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()
from auth_helpers import register_verified
