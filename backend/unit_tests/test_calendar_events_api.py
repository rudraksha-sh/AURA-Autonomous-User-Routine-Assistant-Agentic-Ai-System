from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base, get_db
from app.main import app
from app.models.integration import Integration


class FakeEventsRequest:
    def execute(self):
        return {"items": [
            {"id": "meeting", "summary": "Project review", "start": {"dateTime": "2026-10-20T10:00:00+00:00"}, "end": {"dateTime": "2026-10-20T11:00:00+00:00"}},
            {"id": "holiday", "summary": "Holiday", "start": {"date": "2026-10-21"}, "end": {"date": "2026-10-22"}},
            {"id": "free", "summary": "Optional", "transparency": "transparent", "start": {"dateTime": "2026-10-20T12:00:00+00:00"}, "end": {"dateTime": "2026-10-20T13:00:00+00:00"}},
            {"id": "bad", "start": {}, "end": {}},
        ]}


class FakeEvents:
    def list(self, **_kwargs):
        return FakeEventsRequest()


class FakeCalendar:
    def events(self):
        return FakeEvents()


def test_calendar_busy_blocks_auth_fallback_and_external_validation(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'calendar-events.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        account = client.post("/api/auth/register", json={"email": "calendar-view@example.com", "name": "Calendar User", "password": "StrongPass123!"})
        assert account.status_code == 201
        login = client.post("/api/auth/login", json={"email": "calendar-view@example.com", "password": "StrongPass123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        params = {"start_at": "2026-10-19T00:00:00+00:00", "end_at": "2026-10-26T00:00:00+00:00"}

        assert client.get("/api/planner/calendar/events", params=params).status_code == 401
        fallback = client.get("/api/planner/calendar/events", headers=headers, params=params)
        assert fallback.status_code == 200
        assert fallback.json()["calendar_synced"] is False
        assert fallback.json()["busy_blocks"] == []

        with Session(engine) as session:
            user_id = session.query(Integration.user_id).filter_by(provider="google").first()
            assert user_id is None
            from app.models.user import User

            owner_id = session.query(User.id).filter_by(email="calendar-view@example.com").scalar()
            session.add(Integration(user_id=owner_id, provider="google", access_token="test-access-token"))
            session.commit()

        with patch("app.services.calendar_service.build_calendar_service", return_value=FakeCalendar()):
            response = client.get("/api/planner/calendar/events", headers=headers, params=params)
        assert response.status_code == 200
        payload = response.json()
        assert payload["calendar_synced"] is True
        assert [block["id"] for block in payload["busy_blocks"]] == ["meeting", "holiday"]
        assert payload["busy_blocks"][0]["title"] == "Project review"
        assert payload["busy_blocks"][0]["all_day"] is False
        assert payload["busy_blocks"][1]["all_day"] is True
        assert payload["busy_blocks"][1]["end_at"].startswith("2026-10-22T00:00:00")

        invalid_range = client.get("/api/planner/calendar/events", headers=headers, params={"start_at": "2026-10-20T00:00:00", "end_at": "2026-10-21T00:00:00"})
        assert invalid_range.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_calendar_api_failure_returns_clear_unsynced_state(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'calendar-api-error.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        client.post("/api/auth/register", json={"email": "calendar-error@example.com", "name": "Calendar User", "password": "StrongPass123!"})
        login = client.post("/api/auth/login", json={"email": "calendar-error@example.com", "password": "StrongPass123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        with Session(engine) as session:
            from app.models.user import User

            owner_id = session.query(User.id).filter_by(email="calendar-error@example.com").scalar()
            session.add(Integration(user_id=owner_id, provider="google", access_token="test-access-token"))
            session.commit()
        with patch("app.services.calendar_service.build_calendar_service", side_effect=RuntimeError("Google unavailable")):
            response = client.get("/api/planner/calendar/events", headers=headers, params={"start_at": "2026-10-20T00:00:00+00:00", "end_at": "2026-10-21T00:00:00+00:00"})
        assert response.status_code == 200
        assert response.json()["calendar_synced"] is False
        assert "could not be loaded" in response.json()["message"]
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
