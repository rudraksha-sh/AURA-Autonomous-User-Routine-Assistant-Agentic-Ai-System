from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import Base, get_db
from app.main import app


def test_task_board_details_bulk_actions_and_user_scoping(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'task-board.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)

        def account(email: str) -> dict[str, str]:
            response = client.post("/api/auth/register", json={"email": email, "name": "Board Tester", "password": "StrongPass123!"})
            assert response.status_code == 201
            with Session(engine) as session:
                from app.models.user import User

                user = session.query(User).filter_by(email=email).one()
                token = create_access_token({"sub": str(user.id)})
            return {"Authorization": f"Bearer {token}"}

        owner = account("board-owner@example.com")
        other = account("board-other@example.com")
        goal_response = client.post("/api/goals", headers=owner, json={"title": "Board goal"})
        assert goal_response.status_code == 201
        goal_id = goal_response.json()["id"]
        task_response = client.post(f"/api/tasks/goals/{goal_id}/tasks", headers=owner, json={"title": "Review draft"})
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]
        second_response = client.post(f"/api/tasks/goals/{goal_id}/tasks", headers=owner, json={"title": "Send draft"})
        second_id = second_response.json()["id"]

        patched = client.patch(f"/api/tasks/{task_id}", headers=owner, json={"notes": "Check the references", "status": "in_progress"})
        assert patched.status_code == 200
        assert patched.json()["notes"] == "Check the references"

        created_subtask = client.post(f"/api/tasks/{task_id}/subtasks", headers=owner, json={"title": "Verify references"})
        assert created_subtask.status_code == 201
        subtask_id = created_subtask.json()["id"]
        assert client.patch(f"/api/tasks/{task_id}/subtasks/{subtask_id}", headers=owner, json={"is_completed": True}).json()["is_completed"] is True
        activity = client.get(f"/api/tasks/{task_id}/activity", headers=owner)
        assert activity.status_code == 200
        assert {item["action"] for item in activity.json()} >= {"created", "status_changed", "subtask_added", "subtask_updated"}

        assert client.get(f"/api/tasks/{task_id}/subtasks", headers=other).status_code == 404
        assert client.get(f"/api/tasks/{task_id}/activity", headers=other).status_code == 404
        assert client.patch(f"/api/tasks/{task_id}/subtasks/{subtask_id}", headers=other, json={"is_completed": False}).status_code == 404

        cross_user_bulk = client.post("/api/tasks/bulk", headers=other, json={"task_ids": [task_id], "action": "delete"})
        assert cross_user_bulk.status_code == 404
        atomic_bulk = client.post("/api/tasks/bulk", headers=owner, json={"task_ids": [task_id, 999999], "action": "complete"})
        assert atomic_bulk.status_code == 404
        assert client.get(f"/api/tasks/{task_id}", headers=owner).json()["status"] == "in_progress"

        completed = client.post("/api/tasks/bulk", headers=owner, json={"task_ids": [task_id, second_id], "action": "complete"})
        assert completed.status_code == 200
        assert completed.json()["updated_count"] == 2
        assert all(task["status"] == "completed" for task in completed.json()["tasks"])
        deleted = client.post("/api/tasks/bulk", headers=owner, json={"task_ids": [second_id], "action": "delete"})
        assert deleted.status_code == 200
        assert deleted.json()["deleted_count"] == 1
        assert client.get(f"/api/tasks/{second_id}", headers=owner).status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
