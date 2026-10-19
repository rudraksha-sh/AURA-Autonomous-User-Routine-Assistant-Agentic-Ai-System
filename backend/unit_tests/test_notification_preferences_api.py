from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base, get_db
from app.main import app


def test_notification_preferences_are_saved_per_user(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'notifications.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            headers = []
            for email in ("notify-a@example.com", "notify-b@example.com"):
                assert client.post("/api/auth/register", json={"name": "Notify", "email": email, "password": "StrongPass123!"}).status_code == 201
                token = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"}).json()["access_token"]
                headers.append({"Authorization": f"Bearer {token}"})
            assert client.get("/api/notifications/preferences").status_code == 401
            assert client.get("/api/notifications/preferences", headers=headers[0]).json() == {
                "due_soon_reminders": True, "overdue_alerts": True, "weekly_summary": False, "reminder_lead_time_minutes": 60,
            }
            response = client.put("/api/notifications/preferences", headers=headers[0], json={
                "due_soon_reminders": False, "overdue_alerts": True, "weekly_summary": True, "reminder_lead_time_minutes": 1440,
            })
            assert response.status_code == 200
            assert response.json()["reminder_lead_time_minutes"] == 1440
            assert client.get("/api/notifications/preferences", headers=headers[0]).json()["due_soon_reminders"] is False
            assert client.get("/api/notifications/preferences", headers=headers[1]).json()["due_soon_reminders"] is True
            invalid = client.put("/api/notifications/preferences", headers=headers[0], json={
                "due_soon_reminders": True, "overdue_alerts": True, "weekly_summary": False, "reminder_lead_time_minutes": 10,
            })
            assert invalid.status_code == 422
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()
