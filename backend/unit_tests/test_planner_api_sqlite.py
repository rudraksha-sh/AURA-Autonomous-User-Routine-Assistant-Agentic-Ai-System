from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import Base, get_db
from app.main import app


def test_authenticated_plan_preview_and_idempotent_save(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'planner-api.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)

        def create_account(email: str) -> dict[str, str]:
            assert client.post("/api/auth/register", json={"email": email, "name": "Planner", "password": "StrongPass123!"}).status_code == 201
            response = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
            return {"Authorization": f"Bearer {response.json()['access_token']}"}

        owner = create_account("planner-owner@example.com")
        other = create_account("planner-other@example.com")
        goal_response = client.post("/api/goals", headers=owner, json={
            "title": "Finish a portfolio", "description": "Prepare selected design work",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        })
        assert goal_response.status_code == 201
        goal_id = goal_response.json()["id"]
        preview_path = f"/api/planner/goals/{goal_id}/plan"
        save_path = f"/api/planner/goals/{goal_id}/save"

        assert client.post(preview_path, json={"task_count": 5}).status_code == 401
        invalid = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        assert client.post(preview_path, headers={"Authorization": f"Bearer {invalid}"}, json={}).status_code == 401
        assert client.post(preview_path, headers=other, json={}).status_code == 404

        preview = client.post(preview_path, headers=owner, json={"task_count": 5})
        assert preview.status_code == 200
        proposed = preview.json()["tasks"]
        assert len(proposed) == 5
        assert client.get("/api/tasks", headers=owner).json() == []

        save_request = {"idempotency_key": "4a66ea66-8e23-4f89-9895-b4590523ec12", "tasks": proposed}
        assert client.post(save_path, headers=other, json=save_request).status_code == 404
        first = client.post(save_path, headers=owner, json=save_request)
        assert first.status_code == 200
        saved = first.json()["tasks"]
        assert len(saved) == 5
        assert all(task["goal_id"] == goal_id for task in saved)
        assert client.post(save_path, headers=owner, json=save_request).json() == first.json()
        refreshed = TestClient(app).get("/api/tasks", headers=owner)
        assert refreshed.status_code == 200
        assert [task["id"] for task in refreshed.json()] == [task["id"] for task in saved]

        bad = client.post(preview_path, headers=owner, json={"task_count": 99})
        assert bad.status_code == 422
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()
