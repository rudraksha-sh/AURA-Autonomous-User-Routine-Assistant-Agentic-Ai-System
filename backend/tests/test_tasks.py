def register_and_login(client, email):
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "TestPassword@123",
            "name": "Task Test User",
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


def create_goal(client, token, title="Task Test Goal"):
    response = client.post(
        "/api/goals",
        headers=auth_headers(token),
        json={
            "title": title,
            "description": "Goal for task testing",
            "status": "active",
            "priority": "medium",
        },
    )

    assert response.status_code == 201

    return response.json()


def create_task(client, token, goal_id, title="Test Task"):
    response = client.post(
        f"/api/tasks/goals/{goal_id}/tasks",
        headers=auth_headers(token),
        json={
            "title": title,
            "description": "Task created during automated testing",
            "status": "pending",
            "priority": "medium",
            "estimated_minutes": 30,
            "position": 1,
        },
    )

    assert response.status_code == 201

    return response.json()


def test_create_task(client):
    token = register_and_login(
        client,
        "task-create@example.com",
    )

    goal = create_goal(client, token)

    task = create_task(
        client,
        token,
        goal["id"],
    )

    assert task["goal_id"] == goal["id"]
    assert task["title"] == "Test Task"
    assert task["status"] == "pending"
    assert task["priority"] == "medium"
    assert task["estimated_minutes"] == 30
    assert task["position"] == 1


def test_get_goal_tasks(client):
    token = register_and_login(
        client,
        "task-list@example.com",
    )

    goal = create_goal(client, token)

    create_task(
        client,
        token,
        goal["id"],
        "Task One",
    )

    response = client.post(
        f"/api/tasks/goals/{goal['id']}/tasks",
        headers=auth_headers(token),
        json={
            "title": "Task Two",
            "description": "Second task",
            "status": "pending",
            "priority": "high",
            "estimated_minutes": 60,
            "position": 2,
        },
    )

    assert response.status_code == 201

    response = client.get(
        f"/api/tasks/goals/{goal['id']}/tasks",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    tasks = response.json()

    assert len(tasks) == 2
    assert tasks[0]["title"] == "Task One"
    assert tasks[1]["title"] == "Task Two"


def test_get_single_task(client):
    token = register_and_login(
        client,
        "task-single@example.com",
    )

    goal = create_goal(client, token)

    task = create_task(
        client,
        token,
        goal["id"],
    )

    response = client.get(
        f"/api/tasks/{task['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == task["id"]
    assert data["goal_id"] == goal["id"]
    assert data["title"] == "Test Task"


def test_update_task(client):
    token = register_and_login(
        client,
        "task-update@example.com",
    )

    goal = create_goal(client, token)

    task = create_task(
        client,
        token,
        goal["id"],
    )

    response = client.patch(
        f"/api/tasks/{task['id']}",
        headers=auth_headers(token),
        json={
            "title": "Updated Task",
            "status": "completed",
            "priority": "high",
            "estimated_minutes": 45,
            "position": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "Updated Task"
    assert data["status"] == "completed"
    assert data["priority"] == "high"
    assert data["estimated_minutes"] == 45
    assert data["position"] == 2


def test_delete_task(client):
    token = register_and_login(
        client,
        "task-delete@example.com",
    )

    goal = create_goal(client, token)

    task = create_task(
        client,
        token,
        goal["id"],
    )

    response = client.delete(
        f"/api/tasks/{task['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204

    response = client.get(
        f"/api/tasks/{task['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_task_requires_authentication(client):
    response = client.get("/api/tasks/goals/1/tasks")

    assert response.status_code == 401


def test_user_cannot_access_another_users_task(client):
    user1_token = register_and_login(
        client,
        "task-owner@example.com",
    )

    user2_token = register_and_login(
        client,
        "task-attacker@example.com",
    )

    goal = create_goal(
        client,
        user1_token,
        "Private Task Goal",
    )

    task = create_task(
        client,
        user1_token,
        goal["id"],
        "Private Task",
    )

    response = client.get(
        f"/api/tasks/{task['id']}",
        headers=auth_headers(user2_token),
    )

    assert response.status_code == 404


def test_user_cannot_create_task_in_another_users_goal(client):
    user1_token = register_and_login(
        client,
        "goal-owner@example.com",
    )

    user2_token = register_and_login(
        client,
        "task-attacker-2@example.com",
    )

    goal = create_goal(
        client,
        user1_token,
        "Owner Goal",
    )

    response = client.post(
        f"/api/tasks/goals/{goal['id']}/tasks",
        headers=auth_headers(user2_token),
        json={
            "title": "Unauthorized Task",
            "description": "Should not be created",
            "status": "pending",
            "priority": "medium",
            "estimated_minutes": 30,
            "position": 1,
        },
    )

    assert response.status_code == 404