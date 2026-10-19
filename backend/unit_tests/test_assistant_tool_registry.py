from uuid import uuid4

import pytest
from auth_helpers import register_verified
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.db.session import Base, get_db
from app.main import app
from app.models.agent_run import AgentRun
from app.models.goal import Goal
from app.models.task import Task
from app.models.user import User
from app.schemas.assistant import CompleteTaskTool, CreateGoalTool, CreateTaskTool, ListTasksTool
from app.services.assistant_tool_registry import execute_assistant_tool


def test_allowlisted_tools_scope_records_and_make_writes_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'assistant-tools.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = User(email="tool-owner@example.com", password_hash="unused", name="Owner")
        other = User(email="tool-other@example.com", password_hash="unused", name="Other")
        db.add_all([owner, other])
        db.flush()
        owner_goal = Goal(user_id=owner.id, title="Owned goal", status="active")
        other_goal = Goal(user_id=other.id, title="Private goal", status="active")
        db.add_all([owner_goal, other_goal])
        db.flush()
        owner_task = Task(goal_id=owner_goal.id, title="Owned task", status="pending", priority="medium", position=1)
        other_task = Task(goal_id=other_goal.id, title="Private task", status="pending", priority="medium", position=1)
        db.add_all([owner_task, other_task])
        db.commit()

        listed = execute_assistant_tool(db, owner.id, ListTasksTool(tool="list_tasks"))
        assert [task.title for task in listed.tasks or []] == ["Owned task"]

        create_request = CreateGoalTool(tool="create_goal", idempotency_key=uuid4(), title="New goal")
        created = execute_assistant_tool(db, owner.id, create_request)
        replay = execute_assistant_tool(db, owner.id, create_request)
        assert created.result and created.result.id == replay.result.id
        assert replay.replayed is True
        assert db.scalar(select(func.count(AgentRun.id)).where(AgentRun.user_id == owner.id, AgentRun.agent_type == "assistant_tool")) == 1

        with pytest.raises(LookupError, match="Goal not found"):
            execute_assistant_tool(db, owner.id, CreateTaskTool(
                tool="create_task", idempotency_key=uuid4(), goal_id=other_goal.id, title="Cross user task",
            ))
        with pytest.raises(LookupError, match="Task not found"):
            execute_assistant_tool(db, owner.id, CompleteTaskTool(
                tool="complete_task", idempotency_key=uuid4(), task_id=other_task.id,
            ))

        task_request = CreateTaskTool(tool="create_task", idempotency_key=uuid4(), goal_id=owner_goal.id, title="Registry task")
        task_created = execute_assistant_tool(db, owner.id, task_request)
        task_replay = execute_assistant_tool(db, owner.id, task_request)
        assert task_created.result and task_created.result.id == task_replay.result.id
        assert task_replay.replayed is True

        complete_request = CompleteTaskTool(tool="complete_task", idempotency_key=uuid4(), task_id=owner_task.id)
        completed = execute_assistant_tool(db, owner.id, complete_request)
        complete_replay = execute_assistant_tool(db, owner.id, complete_request)
        assert completed.result and completed.result.status == "completed"
        assert complete_replay.replayed is True
    engine.dispose()


def test_idempotency_key_cannot_be_reused_for_a_different_action(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'assistant-tool-key.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="tool-key@example.com", password_hash="unused", name="Key")
        db.add(user)
        db.commit()
        key = uuid4()
        execute_assistant_tool(db, user.id, CreateGoalTool(tool="create_goal", idempotency_key=key, title="First"))
        with pytest.raises(ValueError, match="different action"):
            execute_assistant_tool(db, user.id, CreateGoalTool(tool="create_goal", idempotency_key=key, title="Second"))
    engine.dispose()


def test_tool_api_requires_auth_and_enforces_nested_goal_ownership(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'assistant-tools-api.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)

        def account(email: str) -> dict[str, str]:
            register_verified(client, {
                "email": email, "name": "Assistant", "password": "StrongPass123!",
            })
            login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
            return {"Authorization": f"Bearer {login.json()['access_token']}"}

        owner = account("assistant-owner@example.com")
        other = account("assistant-other@example.com")
        assert client.post("/api/assistant/tools", json={"tool": "list_goals"}).status_code == 401
        own_goal = client.post("/api/goals", headers=owner, json={"title": "Own"}).json()
        foreign_goal = client.post("/api/goals", headers=other, json={"title": "Foreign"}).json()
        own_task = client.post(f"/api/tasks/goals/{own_goal['id']}/tasks", headers=owner, json={"title": "Own task"}).json()
        foreign_task = client.post(f"/api/tasks/goals/{foreign_goal['id']}/tasks", headers=other, json={"title": "Foreign task"}).json()

        rejected_create = client.post("/api/assistant/tools", headers=owner, json={
            "tool": "create_task", "goal_id": foreign_goal["id"], "title": "Cross user", "idempotency_key": str(uuid4()),
        })
        rejected_complete = client.post("/api/assistant/tools", headers=owner, json={
            "tool": "complete_task", "task_id": foreign_task["id"], "idempotency_key": str(uuid4()),
        })
        assert rejected_create.status_code == 404
        assert rejected_complete.status_code == 404

        listed = client.post("/api/assistant/tools", headers=owner, json={"tool": "list_goals"})
        assert listed.status_code == 200
        assert [goal["title"] for goal in listed.json()["goals"]] == ["Own"]
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()
