from datetime import date, datetime, time, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base, get_db
from app.main import app
from app.models.agent_run import AgentRun
from app.models.goal import Goal
from app.models.integration import Integration
from app.models.notification_preference import UserNotificationPreference
from app.models.planning import DailySchedule, ScheduleEntry, UserPlanningPreference
from app.models.task import Task
from app.models.task_detail import TaskActivity, TaskSubtask
from app.models.user import User


def test_export_and_typed_account_deletion_remove_only_the_owner_data(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'account-data.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            auth_headers = []
            for email in ("delete-owner@example.com", "delete-other@example.com"):
                assert client.post("/api/auth/register", json={"name": "Account", "email": email, "password": "StrongPass123!"}).status_code == 201
                token = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"}).json()["access_token"]
                auth_headers.append({"Authorization": f"Bearer {token}"})
            owner_id = client.get("/api/auth/me", headers=auth_headers[0]).json()["id"]
            other_id = client.get("/api/auth/me", headers=auth_headers[1]).json()["id"]
            own_goal = client.post("/api/goals", headers=auth_headers[0], json={"title": "Private goal", "description": "Keep this"}).json()
            own_task = client.post(f"/api/tasks/goals/{own_goal['id']}/tasks", headers=auth_headers[0], json={"title": "Private task", "notes": "Private notes", "estimated_minutes": 30}).json()
            other_goal = client.post("/api/goals", headers=auth_headers[1], json={"title": "Other goal"}).json()
            other_task = client.post(f"/api/tasks/goals/{other_goal['id']}/tasks", headers=auth_headers[1], json={"title": "Other task"}).json()

            with Session(engine) as db:
                schedule = DailySchedule(user_id=owner_id, target_date=date(2026, 10, 19), timezone_name="UTC", status="approved", capacity_minutes=360, idempotency_key="2e23bd0e-995a-4d0e-8f9a-108005a00001")
                db.add_all([
                    UserPlanningPreference(user_id=owner_id, timezone_name="UTC", workday_start=time(9), workday_end=time(17), preferred_session_minutes=50, break_minutes=10, daily_capacity_minutes=360),
                    UserNotificationPreference(user_id=owner_id),
                    Integration(user_id=owner_id, provider="google", access_token="private", scopes="calendar.readonly"),
                    AgentRun(user_id=owner_id, goal_id=own_goal["id"], agent_type="planner", input="private", output="{}", status="completed"),
                    TaskSubtask(task_id=own_task["id"], title="Subtask"),
                    TaskActivity(task_id=own_task["id"], action="created", details={}),
                    schedule,
                ])
                db.flush()
                db.add(ScheduleEntry(schedule_id=schedule.id, task_id=own_task["id"], segment_index=1, start_at=datetime(2026, 10, 19, 9, tzinfo=timezone.utc), end_at=datetime(2026, 10, 19, 9, 30, tzinfo=timezone.utc), duration_minutes=30, explanation="Focus"))
                db.commit()

            exported = client.get("/api/profile/export", headers=auth_headers[0])
            assert exported.status_code == 200
            payload = exported.json()
            assert [goal["title"] for goal in payload["goals"]] == ["Private goal"]
            assert payload["tasks"][0]["notes"] == "Private notes"
            csv_export = client.get("/api/profile/export?format=csv", headers=auth_headers[0])
            assert csv_export.status_code == 200
            assert "attachment; filename=\"aura-export.csv\"" in csv_export.headers["content-disposition"]
            assert "Private goal" in csv_export.text and "Other goal" not in csv_export.text
            assert client.get("/api/profile/export?format=xml", headers=auth_headers[0]).status_code == 422

            assert client.request("DELETE", "/api/profile/account", headers=auth_headers[0], json={"confirmation": "DELETE ACCOUNT"}).status_code == 422
            assert client.request("DELETE", "/api/profile/account", headers=auth_headers[0], json={"confirmation": "DELETE"}).status_code == 204
            assert client.get("/api/auth/me", headers=auth_headers[0]).status_code == 401
            with Session(engine) as db:
                assert db.get(User, owner_id) is None
                assert db.query(Goal).filter_by(user_id=owner_id).count() == 0
                assert db.query(Task).filter_by(goal_id=own_goal["id"]).count() == 0
                assert db.query(AgentRun).filter_by(user_id=owner_id).count() == 0
                assert db.query(Integration).filter_by(user_id=owner_id).count() == 0
                assert db.query(UserPlanningPreference).filter_by(user_id=owner_id).count() == 0
                assert db.query(UserNotificationPreference).filter_by(user_id=owner_id).count() == 0
                assert db.query(DailySchedule).filter_by(user_id=owner_id).count() == 0
                assert db.query(ScheduleEntry).count() == 0
                assert db.query(TaskSubtask).count() == 0
                assert db.query(TaskActivity).filter_by(task_id=own_task["id"]).count() == 0
                assert db.query(TaskActivity).filter_by(task_id=other_task["id"]).count() == 1
                assert db.get(User, other_id) is not None
                assert db.query(Goal).filter_by(user_id=other_id).count() == 1
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()
