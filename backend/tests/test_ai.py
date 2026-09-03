from unittest.mock import patch

from app.schemas.ai import GoalPlan, PlannedTask


def register_and_login(client, email):
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "TestPassword@123",
            "name": "AI Test User",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": "TestPassword@123",
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
    }


def mock_goal_plan():
    return GoalPlan(
        title="Build AI Assistant",
        description="Build a personal AI assistant for task management.",
        priority="high",
        tasks=[
            PlannedTask(
                title="Define requirements",
                description="Define the core assistant requirements.",
                priority="high",
                estimated_minutes=60,
                position=1,
                deadline_offset_days=1,
            ),
            PlannedTask(
                title="Build task management",
                description="Implement task creation and management.",
                priority="medium",
                estimated_minutes=120,
                position=2,
                deadline_offset_days=3,
            ),
            PlannedTask(
                title="Test the assistant",
                description="Test the core assistant functionality.",
                priority="high",
                estimated_minutes=90,
                position=3,
                deadline_offset_days=5,
            ),
        ],
    )


def test_ai_plan_success(client):
    token = register_and_login(
        client,
        "ai-success@example.com",
    )

    plan = mock_goal_plan()

    with patch(
        "app.services.ai_service.generate_goal_plan",
        return_value=plan,
    ):
        response = client.post(
            "/api/ai/plan",
            headers=auth_headers(token),
            json={
                "goal": "Build a personal AI assistant",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "Build AI Assistant"
    assert data["description"] == (
        "Build a personal AI assistant for task management."
    )
    assert data["priority"] == "high"

    assert len(data["tasks"]) == 3
    assert data["tasks"][0]["title"] == "Define requirements"
    assert data["tasks"][1]["title"] == "Build task management"
    assert data["tasks"][2]["title"] == "Test the assistant"


def test_ai_plan_persists_goal_and_tasks(client):
    token = register_and_login(
        client,
        "ai-persistence@example.com",
    )

    plan = mock_goal_plan()

    with patch(
        "app.services.ai_service.generate_goal_plan",
        return_value=plan,
    ):
        response = client.post(
            "/api/ai/plan",
            headers=auth_headers(token),
            json={
                "goal": "Build a personal AI assistant",
            },
        )

    assert response.status_code == 201

    # Verify the generated goal through the API.
    goals_response = client.get(
        "/api/goals",
        headers=auth_headers(token),
    )

    assert goals_response.status_code == 200

    goals = goals_response.json()

    assert len(goals) == 1
    assert goals[0]["title"] == "Build AI Assistant"

    goal_id = goals[0]["id"]

    # Verify generated tasks through the API.
    tasks_response = client.get(
        f"/api/tasks/goals/{goal_id}/tasks",
        headers=auth_headers(token),
    )

    assert tasks_response.status_code == 200

    tasks = tasks_response.json()

    assert len(tasks) == 3

    assert tasks[0]["position"] == 1
    assert tasks[1]["position"] == 2
    assert tasks[2]["position"] == 3

    assert tasks[0]["estimated_minutes"] == 60
    assert tasks[1]["estimated_minutes"] == 120
    assert tasks[2]["estimated_minutes"] == 90


def test_ai_plan_requires_authentication(client):
    response = client.post(
        "/api/ai/plan",
        json={
            "goal": "Build a personal AI assistant",
        },
    )

    assert response.status_code == 401


def test_ai_plan_empty_goal(client):
    token = register_and_login(
        client,
        "ai-empty@example.com",
    )

    response = client.post(
        "/api/ai/plan",
        headers=auth_headers(token),
        json={
            "goal": "",
        },
    )

    assert response.status_code == 422


def test_ai_plan_rejects_oversized_goal(client):
    token = register_and_login(
        client,
        "ai-oversized@example.com",
    )

    oversized_goal = "A" * 2001

    response = client.post(
        "/api/ai/plan",
        headers=auth_headers(token),
        json={
            "goal": oversized_goal,
        },
    )

    assert response.status_code == 422


def test_ai_plan_ai_failure(client):
    token = register_and_login(
        client,
        "ai-failure@example.com",
    )

    with patch(
        "app.services.ai_service.generate_goal_plan",
        side_effect=RuntimeError("Simulated AI failure"),
    ):
        response = client.post(
            "/api/ai/plan",
            headers=auth_headers(token),
            json={
                "goal": "Build a personal AI assistant",
            },
        )

    assert response.status_code == 500

    data = response.json()

    assert data["error"] == "internal_server_error"
    assert data["message"] == "An unexpected error occurred"
    assert "Simulated AI failure" not in response.text


def test_ai_plan_ai_failure_does_not_create_goal(client):
    token = register_and_login(
        client,
        "ai-rollback@example.com",
    )

    with patch(
        "app.services.ai_service.generate_goal_plan",
        side_effect=RuntimeError("Simulated AI failure"),
    ):
        response = client.post(
            "/api/ai/plan",
            headers=auth_headers(token),
            json={
                "goal": "This goal should not be persisted",
            },
        )

    assert response.status_code == 500

    goals_response = client.get(
        "/api/goals",
        headers=auth_headers(token),
    )

    assert goals_response.status_code == 200
    assert goals_response.json() == []
    
def test_ai_plan_creates_agent_run(client):
    token = register_and_login(
        client,
        "ai-agent-run@example.com",
    )

    plan = mock_goal_plan()

    with patch(
        "app.services.ai_service.generate_goal_plan",
        return_value=plan,
    ):
        response = client.post(
            "/api/ai/plan",
            headers=auth_headers(token),
            json={
                "goal": "Build a personal AI assistant",
            },
        )

    assert response.status_code == 201

    # The public API does not expose AgentRun directly,
    # so verify it through PostgreSQL.
    from sqlalchemy import text

    from app.db.session import engine

    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT user_id, goal_id, agent_type, status, input, output
                FROM agent_runs
                ORDER BY id DESC
                LIMIT 1
                """
            )
        )

        agent_run = result.mappings().first()

    assert agent_run is not None
    assert agent_run["agent_type"] == "planner"
    assert agent_run["status"] == "completed"
    assert agent_run["input"] == "Build a personal AI assistant"
    assert agent_run["output"] is not None