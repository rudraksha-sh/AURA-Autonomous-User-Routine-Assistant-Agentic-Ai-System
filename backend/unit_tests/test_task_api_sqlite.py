from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base, get_db
from app.main import app
from app.core.security import create_access_token


def test_task_crud_persistence_and_user_isolation(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'task-api.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)

        def create_account(email: str) -> str:
            registration = client.post(
                "/api/auth/register",
                json={"email": email, "name": "Task Test", "password": "StrongPass123!"},
            )
            assert registration.status_code == 201
            login = client.post(
                "/api/auth/login",
                json={"email": email, "password": "StrongPass123!"},
            )
            assert login.status_code == 200
            return login.json()["access_token"]

        owner_token = create_account("task-owner-api@example.com")
        other_token = create_account("task-other-api@example.com")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        other_headers = {"Authorization": f"Bearer {other_token}"}

        assert client.get("/api/goals").status_code == 401
        assert client.get("/api/tasks").status_code == 401
        assert client.get("/api/goals", headers={"Authorization": "Bearer invalid"}).status_code == 401
        expired_token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        assert client.get("/api/tasks", headers={"Authorization": f"Bearer {expired_token}"}).status_code == 401

        goal_response = client.post(
            "/api/goals",
            headers=owner_headers,
            json={"title": "Persisted goal"},
        )
        assert goal_response.status_code == 201
        goal_id = goal_response.json()["id"]
        assert client.get(f"/api/goals/{goal_id}", headers=owner_headers).status_code == 200
        assert client.get(f"/api/goals/{goal_id}", headers=other_headers).status_code == 404
        assert client.patch(f"/api/goals/{goal_id}", headers=other_headers, json={"title": "stolen"}).status_code == 404
        assert client.delete(f"/api/goals/{goal_id}", headers=other_headers).status_code == 404

        created = client.post(
            f"/api/tasks/goals/{goal_id}/tasks",
            headers=owner_headers,
            json={
                "title": "Initial title",
                "description": "Initial details",
                "priority": "low",
                "deadline": "2026-10-20T12:00:00Z",
            },
        )
        assert created.status_code == 201
        task_id = created.json()["id"]
        assert client.get(f"/api/tasks/goals/{goal_id}/tasks", headers=other_headers).status_code == 404
        assert client.post(
            f"/api/tasks/goals/{goal_id}/tasks",
            headers=other_headers,
            json={"title": "Cross-user task"},
        ).status_code == 404
        assert client.get(f"/api/tasks/{task_id}", headers=other_headers).status_code == 404
        assert client.patch(f"/api/tasks/{task_id}", headers=other_headers, json={"title": "stolen"}).status_code == 404
        assert client.delete(f"/api/tasks/{task_id}", headers=other_headers).status_code == 404

        updated = client.patch(
            f"/api/tasks/{task_id}",
            headers=owner_headers,
            json={
                "title": "Updated title",
                "description": "Updated details",
                "status": "completed",
                "priority": "high",
                "deadline": "2026-10-22T12:00:00Z",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["title"] == "Updated title"
        assert updated.json()["description"] == "Updated details"
        assert updated.json()["status"] == "completed"
        assert updated.json()["priority"] == "high"

        reopened = client.patch(
            f"/api/tasks/{task_id}",
            headers=owner_headers,
            json={"status": "pending"},
        )
        assert reopened.status_code == 200
        assert reopened.json()["status"] == "pending"

        refreshed_client = TestClient(app)
        owner_tasks = refreshed_client.get("/api/tasks", headers=owner_headers)
        other_tasks = refreshed_client.get("/api/tasks", headers=other_headers)
        assert owner_tasks.status_code == 200
        assert [task["id"] for task in owner_tasks.json()] == [task_id]
        assert other_tasks.status_code == 200
        assert other_tasks.json() == []

        deleted = refreshed_client.delete(f"/api/tasks/{task_id}", headers=owner_headers)
        assert deleted.status_code == 204
        assert refreshed_client.get("/api/tasks", headers=owner_headers).json() == []
        assert refreshed_client.get(f"/api/tasks/{task_id}", headers=owner_headers).status_code == 404

        deleted_goal = refreshed_client.delete(f"/api/goals/{goal_id}", headers=owner_headers)
        assert deleted_goal.status_code == 204
        assert refreshed_client.get(f"/api/goals/{goal_id}", headers=owner_headers).status_code == 404

        logout_response = refreshed_client.post("/api/auth/logout", headers=owner_headers)
        assert logout_response.status_code == 204
        assert refreshed_client.get("/api/auth/me", headers=owner_headers).status_code == 401
        assert refreshed_client.get("/api/goals", headers=owner_headers).status_code == 401
        assert refreshed_client.get("/api/tasks", headers=owner_headers).status_code == 401

        new_login = refreshed_client.post(
            "/api/auth/login",
            json={"email": "task-owner-api@example.com", "password": "StrongPass123!"},
        )
        assert new_login.status_code == 200
        new_headers = {"Authorization": f"Bearer {new_login.json()['access_token']}"}
        assert refreshed_client.get("/api/auth/me", headers=new_headers).status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
