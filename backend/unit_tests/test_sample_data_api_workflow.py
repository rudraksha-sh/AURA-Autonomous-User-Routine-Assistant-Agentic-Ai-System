
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session

from auth_helpers import register_verified
from app.db.session import Base, get_db
from app.main import app
from app.models.task import Task
from app.models.user import User
from scripts.seed_sample_data import _safe_database_url


def _is_overdue(task: dict) -> bool:
    if task["status"] == "completed" or not task["deadline"]:
        return False

    deadline = datetime.fromisoformat(task["deadline"])
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    return deadline < datetime.now(timezone.utc)


def test_seed_database_guard_rejects_non_sqlite_and_outside_paths(monkeypatch):
    monkeypatch.setenv(
        "AURA_SEED_DATABASE_URL",
        "postgresql://localhost/production",
    )
    with pytest.raises(SystemExit, match="dedicated SQLite"):
        _safe_database_url()

    monkeypatch.setenv(
        "AURA_SEED_DATABASE_URL",
        "sqlite:///../aura_dev.db",
    )
    with pytest.raises(
        SystemExit,
        match="outside the dedicated sample test directory",
    ):
        _safe_database_url()


def test_authenticated_goal_task_planner_dashboard_data_and_persistence(
    tmp_path,
):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'aura-api-workflow-test.db'}"
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            assert client.get("/api/goals").status_code == 401
            assert client.get(
                "/api/goals",
                headers={"Authorization": "Bearer invalid-token"},
            ).status_code == 401

            register_verified(
                client,
                {
                    "email": "api-flow@example.com",
                    "name": "API Flow",
                    "password": "SafeTestPassword123!",
                },
            )

            login = client.post(
                "/api/auth/login",
                json={
                    "email": "api-flow@example.com",
                    "password": "SafeTestPassword123!",
                },
            )
            assert login.status_code == 200

            headers = {
                "Authorization": f"Bearer {login.json()['access_token']}"
            }
            assert client.get(
                "/api/auth/me",
                headers=headers,
            ).status_code == 200

            goal_response = client.post(
                "/api/goals",
                headers=headers,
                json={
                    "title": "Prepare for Machine Learning exams within 14 days",
                    "description": (
                        "Review core concepts and practice model implementations."
                    ),
                    "priority": "high",
                    "deadline": (
                        datetime.now(timezone.utc) + timedelta(days=14)
                    ).isoformat(),
                },
            )
            assert goal_response.status_code == 201

            goal = goal_response.json()
            goal_id = goal["id"]

            # Keep this integration test deterministic instead of calling
            # the live OpenRouter provider twice.
            with Session(engine) as session:
                session.execute(
                    update(User)
                    .where(User.email == "api-flow@example.com")
                    .values(use_ai_planning=False)
                )
                session.commit()

            task_specs = [
                ("Study Python and NumPy", 60, "high", "completed", -2),
                (
                    "Learn linear and logistic regression",
                    90,
                    "high",
                    "in_progress",
                    1,
                ),
                (
                    "Complete ML coding exercises",
                    45,
                    "medium",
                    "pending",
                    -1,
                ),
            ]

            created_tasks = []

            for position, (
                title,
                estimate,
                priority,
                task_status,
                deadline_offset,
            ) in enumerate(task_specs, 1):
                response = client.post(
                    f"/api/tasks/goals/{goal_id}/tasks",
                    headers=headers,
                    json={
                        "title": title,
                        "description": f"Work session for {title.lower()}.",
                        "estimated_minutes": estimate,
                        "priority": priority,
                        "status": task_status,
                        "position": position,
                        "deadline": (
                            datetime.now(timezone.utc)
                            + timedelta(days=deadline_offset)
                        ).isoformat(),
                    },
                )
                assert response.status_code == 201
                created_tasks.append(response.json())

            invalid_task = client.post(
                f"/api/tasks/goals/{goal_id}/tasks",
                headers=headers,
                json={
                    "title": "Invalid estimate",
                    "estimated_minutes": 0,
                },
            )
            assert invalid_task.status_code == 422

            tasks_response = client.get("/api/tasks", headers=headers)
            assert tasks_response.status_code == 200
            assert len(tasks_response.json()) == 3

            own_task = created_tasks[1]

            patch = client.patch(
                f"/api/tasks/{own_task['id']}",
                headers=headers,
                json={
                    "title": "Learn regression models",
                    "status": "completed",
                },
            )
            assert patch.status_code == 200
            assert patch.json()["status"] == "completed"

            assert client.get(
                f"/api/tasks/{own_task['id']}",
                headers=headers,
            ).status_code == 200

            list_goals = client.get("/api/goals", headers=headers)
            assert list_goals.status_code == 200
            assert len(list_goals.json()) == 1

            tasks = client.get("/api/tasks", headers=headers).json()
            completed_count = sum(
                task["status"] == "completed" for task in tasks
            )
            overdue_count = sum(_is_overdue(task) for task in tasks)

            assert completed_count == 2
            assert overdue_count == 1

            today = date.today().isoformat()

            preview = client.post(
                "/api/planner/schedules/preview",
                headers=headers,
                json={"target_date": today},
            )
            assert preview.status_code == 200
            assert preview.json()["scheduled_minutes"] > 0

            proposed = preview.json()["entries"]

            if proposed:
                save = client.post(
                    "/api/planner/schedules",
                    headers=headers,
                    json={
                        "idempotency_key": (
                            "f40b625b-935e-4e0d-a26e-35b10ef616f8"
                        ),
                        "target_date": today,
                        "entries": [
                            {
                                "task_id": item["task_id"],
                                "start_at": item["start_at"],
                                "duration_minutes": item[
                                    "duration_minutes"
                                ],
                            }
                            for item in proposed
                        ],
                    },
                )
                assert save.status_code == 201

                saved_schedule = client.get(
                    f"/api/planner/schedules/day/{today}",
                    headers=headers,
                )
                assert saved_schedule.status_code == 200
                assert (
                    saved_schedule.json()["schedule"]["id"]
                    == save.json()["id"]
                )

            goal_plan_a = client.post(
                f"/api/planner/goals/{goal_id}/plan",
                headers=headers,
                json={"task_count": 5},
            )
            goal_plan_b = client.post(
                f"/api/planner/goals/{goal_id}/plan",
                headers=headers,
                json={"task_count": 5},
            )

            assert goal_plan_a.status_code == 200
            assert goal_plan_b.status_code == 200
            assert goal_plan_a.json() == goal_plan_b.json()
            assert len(goal_plan_a.json()["tasks"]) == 5

            register_verified(
                client,
                {
                    "email": "api-other@example.com",
                    "name": "Other",
                    "password": "AnotherSafe123!",
                },
            )

            other_login = client.post(
                "/api/auth/login",
                json={
                    "email": "api-other@example.com",
                    "password": "AnotherSafe123!",
                },
            )
            assert other_login.status_code == 200

            other_headers = {
                "Authorization": (
                    f"Bearer {other_login.json()['access_token']}"
                )
            }

            assert client.get(
                f"/api/goals/{goal_id}",
                headers=other_headers,
            ).status_code == 404

            assert client.patch(
                f"/api/tasks/{own_task['id']}",
                headers=other_headers,
                json={"status": "pending"},
            ).status_code == 404

            assert client.delete(
                f"/api/tasks/{own_task['id']}",
                headers=other_headers,
            ).status_code == 404

            assert client.post(
                f"/api/planner/goals/{goal_id}/plan",
                headers=other_headers,
                json={"task_count": 5},
            ).status_code == 404

            logout = client.post(
                "/api/auth/logout",
                headers=headers,
            )
            assert logout.status_code == 204

            assert client.get(
                "/api/goals",
                headers=headers,
            ).status_code == 401

            with Session(engine) as fresh_session:
                persisted = (
                    fresh_session.query(Task)
                    .filter_by(goal_id=goal_id)
                    .all()
                )
                assert len(persisted) == 3
                assert sum(
                    task.status == "completed" for task in persisted
                ) == 2

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def test_goal_delete_and_task_delete_are_persisted(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'aura-api-delete-test.db'}"
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            register_verified(
                client,
                {
                    "email": "delete@example.com",
                    "name": "Delete",
                    "password": "SafeTestPassword123!",
                },
            )

            login = client.post(
                "/api/auth/login",
                json={
                    "email": "delete@example.com",
                    "password": "SafeTestPassword123!",
                },
            )
            assert login.status_code == 200

            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            goal_response = client.post(
                "/api/goals",
                headers=headers,
                json={"title": "Delete test goal"},
            )
            assert goal_response.status_code == 201
            goal_id = goal_response.json()["id"]

            task_response = client.post(
                f"/api/tasks/goals/{goal_id}/tasks",
                headers=headers,
                json={"title": "Temporary sample task"},
            )
            assert task_response.status_code == 201
            task_id = task_response.json()["id"]

            assert client.delete(
                f"/api/tasks/{task_id}",
                headers=headers,
            ).status_code == 204

            assert client.get(
                f"/api/tasks/{task_id}",
                headers=headers,
            ).status_code == 404

            assert client.delete(
                f"/api/goals/{goal_id}",
                headers=headers,
            ).status_code == 204

            assert client.get(
                f"/api/goals/{goal_id}",
                headers=headers,
            ).status_code == 404

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()
