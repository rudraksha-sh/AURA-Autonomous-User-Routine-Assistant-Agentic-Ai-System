from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.planner import service as planner_service
from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.agent_run import AgentRun
from app.models.goal import Goal
from app.models.task import Task


def test_ai_endpoint_uses_deterministic_fallback_and_persists_real_records(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'ai-fallback-api-test.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "ai_provider", "openrouter")
    try:
        with TestClient(app) as client:
            assert client.get("/api/ai/status").status_code == 401
            assert client.post("/api/ai/plan", json={"goal": "Study machine learning"}).status_code == 401
            registered = client.post("/api/auth/register", json={
                "email": "planner-fallback@example.com",
                "name": "Planner Test",
                "password": "SafeTestPassword123!",
            })
            assert registered.status_code == 201
            login = client.post("/api/auth/login", json={
                "email": "planner-fallback@example.com", "password": "SafeTestPassword123!",
            })
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            status_response = client.get("/api/ai/status", headers=headers)
            assert status_response.status_code == 200
            assert status_response.json() == {
                "provider": "openrouter", "configured": False, "fallback_available": True,
            }
            assert client.get("/api/profile/ai-planning", headers=headers).json() == {"use_ai_planning": True}
            calls = []
            monkeypatch.setattr(planner_service, "_load_provider", lambda: calls.append("provider") or None)
            preference = client.put("/api/profile/ai-planning", headers=headers, json={"use_ai_planning": False})
            assert preference.status_code == 200
            headers = {"Authorization": f"Bearer {preference.json()['access_token']}"}
            disabled_plan = client.post("/api/ai/plan", headers=headers, json={"goal": "Plan without AI"})
            assert disabled_plan.status_code == 201
            assert disabled_plan.json()["generation_mode"] == "rule_based"
            assert calls == []
            assert client.post("/api/ai/plan", headers=headers, json={"goal": "   "}).status_code == 422
            created = client.post("/api/ai/plan", headers=headers, json={"goal": "Study machine learning"})
            assert created.status_code == 201
            plan = created.json()
            assert plan["generation_mode"] == "rule_based"
            assert "not interpreted by a language model" in plan["description"]
            assert len(plan["tasks"]) == 5

            goals = client.get("/api/goals", headers=headers)
            assert goals.status_code == 200
            assert len(goals.json()) == 2
            goal_id = goals.json()[-1]["id"]
            tasks = client.get(f"/api/tasks/goals/{goal_id}/tasks", headers=headers)
            assert tasks.status_code == 200
            assert len(tasks.json()) == 5
            assert {task["goal_id"] for task in tasks.json()} == {goal_id}

            with Session(engine) as fresh_session:
                assert fresh_session.query(AgentRun).filter_by(user_id=goals.json()[0]["user_id"], agent_type="planner", status="completed").count() == 2
                assert fresh_session.query(Goal).filter_by(id=goal_id).count() == 1
                assert fresh_session.query(Task).filter_by(goal_id=goal_id).count() == 5
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def test_provider_errors_fall_back_without_exposing_provider_exception(monkeypatch):
    class BrokenProvider:
        name = "openrouter"

        def generate(self, _goal: str):
            raise RuntimeError("secret-token-must-not-escape")

    monkeypatch.setattr(planner_service, "_load_provider", lambda: BrokenProvider())
    plan = planner_service.generate_goal_plan("Build a study routine")
    assert plan.generation_mode == "rule_based"
    assert len(plan.tasks) == 5
    assert "secret-token-must-not-escape" not in plan.model_dump_json()


def test_provider_success_is_validated_and_marked_as_provider_generated(monkeypatch):
    class GoodProvider:
        name = "openrouter"

        def generate(self, _goal: str):
            return planner_service.ProviderGoalPlan(
                title="Reviewed plan",
                description="Structured response",
                priority="high",
                tasks=[{
                    "title": "Read chapter one",
                    "description": "Review chapter one.",
                    "priority": "high",
                    "estimated_minutes": 45,
                    "position": 1,
                    "deadline_offset_days": None,
                }],
            )

    monkeypatch.setattr(planner_service, "_load_provider", lambda: GoodProvider())
    plan = planner_service.generate_goal_plan("Study")
    assert plan.generation_mode == "openrouter"
    assert plan.tasks[0].title == "Read chapter one"
