from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base, get_db
from app.main import app


def test_authenticated_daily_schedule_preview_approval_and_isolation(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'daily-planner-api.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)

        def create_account(email: str) -> dict[str, str]:
            assert client.post("/api/auth/register", json={
                "email": email, "name": "Daily plan", "password": "StrongPass123!",
            }).status_code == 201
            response = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
            return {"Authorization": f"Bearer {response.json()['access_token']}"}

        owner = create_account("daily-plan-owner@example.com")
        other = create_account("daily-plan-other@example.com")
        assert client.get("/api/planner/preferences").status_code == 401
        goal = client.post("/api/goals", headers=owner, json={"title": "Write a report"}).json()
        task = client.post(f"/api/tasks/goals/{goal['id']}/tasks", headers=owner, json={
            "title": "Draft outline", "priority": "high", "estimated_minutes": 80,
            "deadline": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        }).json()

        saved_preferences = client.put("/api/planner/preferences", headers=owner, json={
            "timezone_name": "America/New_York", "workday_start": "09:00:00", "workday_end": "17:00:00",
            "preferred_session_minutes": 40, "break_minutes": 10, "daily_capacity_minutes": 300,
        })
        assert saved_preferences.status_code == 200
        assert saved_preferences.json()["timezone_name"] == "America/New_York"
        assert client.get("/api/planner/preferences", headers=other).json()["timezone_name"] == "UTC"

        preview = client.post("/api/planner/schedules/preview", headers=owner, json={"target_date": "2026-10-19"})
        assert preview.status_code == 200
        assert len(preview.json()["entries"]) == 2
        assert all(item["task_id"] == task["id"] for item in preview.json()["entries"])

        body = {
            "idempotency_key": "b69369ce-b8ad-4e3f-9c73-815ff4008b9e",
            "target_date": "2026-10-19",
            "entries": [
                {"task_id": task["id"], "start_at": "2026-10-19T09:00:00-04:00", "duration_minutes": 40},
                {"task_id": task["id"], "start_at": "2026-10-19T09:50:00-04:00", "duration_minutes": 40},
            ],
        }
        assert client.post("/api/planner/schedules", headers=other, json=body).status_code == 404
        approved = client.post("/api/planner/schedules", headers=owner, json=body)
        assert approved.status_code == 201
        assert approved.json()["status"] == "approved"
        assert len(approved.json()["entries"]) == 2
        assert client.post("/api/planner/schedules", headers=owner, json=body).json() == approved.json()
        assert client.get("/api/planner/schedules/day/2026-10-19", headers=owner).json()["schedule"]["id"] == approved.json()["id"]
        assert client.get("/api/planner/schedules/day/2026-10-19", headers=other).json()["schedule"] is None
        assert client.delete("/api/planner/schedules/day/2026-10-19", headers=other).status_code == 204
        assert client.get("/api/planner/schedules/day/2026-10-19", headers=owner).json()["schedule"]["id"] == approved.json()["id"]
        assert client.delete("/api/planner/schedules/day/2026-10-19", headers=owner).status_code == 204
        assert client.get("/api/planner/schedules/day/2026-10-19", headers=owner).json()["schedule"] is None
        assert client.get("/api/tasks", headers=owner).json()[0]["status"] == "pending"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()


def test_what_if_endpoint_requires_auth_and_isolates_user_data(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'what-if-api.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)

        def register_and_login(email: str) -> dict[str, str]:
            assert client.post("/api/auth/register", json={
                "email": email, "name": "Simulator", "password": "StrongPass123!",
            }).status_code == 201
            response = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
            return {"Authorization": f"Bearer {response.json()['access_token']}"}

        owner = register_and_login("what-if-owner@example.com")
        other = register_and_login("what-if-other@example.com")
        body = {
            "target_date": "2026-10-19",
            "proposed_task": {"title": "Scenario only", "estimated_minutes": 30, "priority": "high"},
        }
        assert client.post("/api/planner/schedules/what-if", json=body).status_code == 401
        result = client.post("/api/planner/schedules/what-if", headers=owner, json=body)
        assert result.status_code == 200
        assert result.json()["simulated"]["entries"][0]["is_proposed_task"] is True
        assert client.get("/api/tasks", headers=owner).json() == []
        assert client.get("/api/tasks", headers=other).json() == []
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()
